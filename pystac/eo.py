from pystac.item import Item, Asset
from pystac import STACError


class EOItem(Item):
    EO_FIELDS = ['gsd', 'platform', 'instrument', 'bands', 'constellation', 'epsg',
                 'cloud_cover', 'off_nadir', 'azimuth', 'sun_azimuth', 'sun_elevation']

    def __init__(self,
                 id,
                 geometry,
                 bbox,
                 datetime,
                 properties,
                 gsd,
                 platform,
                 instrument,
                 bands,
                 constellation=None,
                 epsg=None,
                 cloud_cover=None,
                 off_nadir=None,
                 azimuth=None,
                 sun_azimuth=None,
                 sun_elevation=None,
                 stac_extensions=['eo'],
                 href=None,
                 collection=None,
                 assets={}):
        super().__init__(id, geometry, bbox, datetime,
                         properties, stac_extensions, href,
                         collection)
        self.gsd = gsd
        self.platform = platform
        self.instrument = instrument
        self.bands = [Band.from_dict(b) for b in bands]
        self.constellation = constellation
        self.epsg = epsg
        self.cloud_cover = cloud_cover
        self.off_nadir = off_nadir
        self.azimuth = azimuth
        self.sun_azimuth = sun_azimuth
        self.sun_elevation = sun_elevation

    def __repr__(self):
        return '<EOItem id={}>'.format(self.id)

    @staticmethod
    def from_dict(d):
        item = Item.from_dict(d)
        return EOItem.from_item(item)

    @classmethod
    def from_item(cls, item):
        eo_params = {}
        for eof in EOItem.EO_FIELDS:
            if eo_key(eof) in item.properties.keys():
                eo_params[eof] = item.properties[eo_key(eof)]
            elif eof in ('gsd', 'platform', 'instrument', 'bands'):
                raise STACError(
                    "Missing required field '{}' in properties".format(eo_key(eof)))

        e = cls(item.id, item.geometry, item.bbox, item.datetime,
                item.properties, stac_extensions=item.stac_extensions,
                collection=item.collection, **eo_params)

        e.links = item.links
        e.assets = item.assets

        for k, v in item.assets.items():
            if v.is_eo():
                e.assets[k] = EOAsset.from_asset(v)
            e.assets[k].set_owner(e)

        return e

    def get_eo_assets(self):
        return {k: v for k, v in self.assets.items() if isinstance(v, EOAsset)}

    def add_asset(self, key, asset):
        if asset.is_eo() and not isinstance(asset, EOAsset):
            asset = EOAsset.from_asset(asset)
        asset.set_owner(self)
        self.assets[key] = asset
        return self

    @staticmethod
    def from_file(uri):
        return EOItem.from_item(Item.from_file(uri))

    def clone(self):
        c = super(EOItem, self).clone()
        return EOItem.from_item(c)

    def to_dict(self):
        d = super().to_dict()
        for eof in EOItem.EO_FIELDS:
            if eo_key(eof) in d['properties'].keys():
                d[eo_key(eof)] = d['properties'][eo_key(eof)]
        return d


class EOAsset(Asset):
    def __init__(self, href, bands, title=None, media_type=None, properties=None):
        super().__init__(href, title, media_type, properties)
        self.bands = bands

    @staticmethod
    def from_dict(d):
        asset = Asset.from_dict(d)
        return EOAsset.from_asset(asset)

    @classmethod
    def from_asset(cls, asset):
        a = asset.clone()
        bands = a.properties.get('eo:bands')
        return cls(a.href, bands, a.title, a.media_type, a.properties)

    def clone(self):
        c = super().clone()
        return EOAsset.from_asset(c)

    def __repr__(self):
        return '<EOAsset href={}>'.format(self.href)

    def get_band_objs(self):
        # Not sure exactly how this method fits in but
        # it seems like there should be a way to get the
        # Band objects associated with the indices
        if not self.item:
            raise STACError('Asset is currently not associated with an item')
        return [self.item.bands[i] for i in self.bands]


class Band:
    def __init__(self,
                 name=None,
                 common_name=None,
                 gsd=None,
                 center_wavelength=None,
                 full_width_max=None,
                 description=None,
                 accuracy=None):
        self.name = name
        self.common_name = common_name
        self.gsd = gsd
        self.center_wavelength = center_wavelength
        self.full_width_max = full_width_max
        # neither of these are in the examples so autogenerating
        # description
        self.description = description
        if not self.description:
            self.description = band_desc(self.common_name)
        self.accuracy = accuracy

    def __repr__(self):
        return '<Band name={}>'.format(self.name)

    @staticmethod
    def from_dict(d):
        name = d.get('name', None)
        common_name = d.get('common_name', None)
        gsd = d.get('gsd', None)
        center_wavelength = d.get('center_wavelength', None)
        full_width_max = d.get('full_width_max', None)
        description = d.get('description', None)
        accuracy = d.get('accuracy', None)

        return Band(name, common_name, gsd, center_wavelength,
                    full_width_max, description, accuracy)

    def to_dict(self):
        d = {}
        if self.name:
            d['name'] = self.name
        if self.common_name:
            d['common_name'] = self.common_name
        if self.gsd:
            d['gsd'] = self.gsd
        if self.center_wavelength:
            d['center_wavelength'] = self.center_wavelength
        if self.full_width_max:
            d['full_width_max'] = self.full_width_max
        if self.description:
            d['description'] = self.description
        if self.accuracy:
            d['accuracy'] = self.accuracy
        return d


def eo_key(key):
    return 'eo:{}'.format(key)


def band_range(common_name):
    name_to_range = {
        'coastal': (0.40, 0.45),
        'blue': (0.45, 0.50),
        'green': (0.50, 0.60),
        'red': (0.60, 0.70),
        'yellow': (0.58, 0.62),
        'pan': (0.50, 0.70),
        'rededge': (0.70, 0.75),
        'nir': (0.75, 1.00),
        'nir08': (0.75, 0.90),
        'nir09': (0.85, 1.05),
        'cirrus': (1.35, 1.40),
        'swir16': (1.55, 1.75),
        'swir22': (2.10, 2.30),
        'lwir': (10.5, 12.5),
        'lwir11': (10.5, 11.5),
        'lwir12': (11.5, 12.5)
    }
    return name_to_range.get(common_name, common_name)


def band_desc(common_name):
    r = band_range(common_name)
    if not r:
        return "Common name: {}".format(common_name)
    return "Common name: {}, Range: {} to {}".format(common_name, r[0], r[1])
