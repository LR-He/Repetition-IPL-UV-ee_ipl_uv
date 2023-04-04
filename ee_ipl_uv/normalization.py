'''
Created on June 15, 2016

@author:  Gonzalo Mateo Garcia
@contact: gonzalo.mateo-garcia@uv.es

'''
import ee


def ComputeNormalizationFeatureCollection(feature_collection,
                                          bands_to_normalize,
                                          only_center_data=False,
                                          weight=None):
    """
    Compute normalization: returns the feature_collection normalized together with the mean
    and std.

    >>> ee.Initialize()

    >>> im = ee.Image('LANDSAT/LC8_L1T_TOA/LC81980332015119LGN00').select(["B2","B3"])
    >>> ftcol = im.sample(numPixels=10,seed=23)
    >>> ftcol_norm, mean, std = ComputeNormalizationFeatureCollection(ftcol,["B2","B3"])

    :param feature_collection:
    :param bands_to_normalize:
    :param only_center_data: if
    :param weight: weight column
    :return: feature_collection normalized, dictionary with mean of each band, dict with
    sd of each band
    :rtype ee.FeatureCollection, ee.Dictionary, ee.Dictionary
    """
    bands_to_normalize_server = ee.List(bands_to_normalize)
    if weight is not None:
        weights = [weight for b in bands_to_normalize]
        mean = feature_collection.reduceColumns(
            # reducer=ee.Reducer.mean().repeat(ee.Number(bands_to_normalize.size())),
            reducer=ee.Reducer.mean().forEach(bands_to_normalize_server),
            selectors=bands_to_normalize_server,
            weightSelectors=weights
        )
    else:
        mean = feature_collection.reduceColumns(
            # reducer=ee.Reducer.mean().repeat(ee.Number(bands_to_normalize.size())),
            reducer=ee.Reducer.mean().forEach(bands_to_normalize_server),
            selectors=bands_to_normalize_server
        )
       # 表示在“selectors”中的每一个波段都应用“reducer”中的均值缩减器，
      # 并将得到的值通过“reduceColumns”返回一个字典，key名称为输出名称。

    if not only_center_data:
        sd = feature_collection.reduceColumns(
            reducer=ee.Reducer.stdDev().forEach(bands_to_normalize_server),
            selectors=bands_to_normalize_server)
        # 计算标准差值
    else:
        sd = None

    def NormalizeFeature(feature):
        feature = ee.Feature(feature)

        if not only_center_data:
            values = bands_to_normalize_server.map(
                lambda bn: ee.Number(feature.get(bn)).subtract(mean.get(bn)).divide(sd.get(bn)))
            # 归一化（标准化）操作
        else:
            values = bands_to_normalize_server.map(
                lambda bn: ee.Number(feature.get(bn)).subtract(mean.get(bn)))

        dictio = ee.Dictionary.fromLists(bands_to_normalize_server, values) # 构建字典，将名称和值对应起来组成字典
        return feature.setMulti(dictio)
                # feature.setMulti() 通过在将一个或多个指定属性设置或重置为指定值后复制指定特性来创建新特性。

    return feature_collection.map(NormalizeFeature), mean, sd


def ApplyToFeature(properties, function):
    properties = ee.List(properties)

    def funcion_apply(feature_iter):
        feature_iter = ee.Feature(feature_iter)
        values = properties.map(lambda bn: function(ee.Number(feature_iter.get(bn))))
        dictio = ee.Dictionary.fromLists(properties, values)
        return feature_iter.setMulti(dictio)
    return funcion_apply


def ApplyNormalizationImage(img, bands, mean, sd):
    for band in bands:
        im_copy = img.select(band)
        if sd is not None:
            im_copy = im_copy.subtract(ee.Number(mean.get(band))).divide(ee.Number(sd.get(band)))
        else:
            im_copy = im_copy.subtract(ee.Number(mean.get(band)))
        img = img.addBands(im_copy, overwrite=True)
    return img


def ApplyDenormalizationImage(img, bands, mean, sd=None):
    for band in bands:
        im_copy = img.select(band)
        if sd is not None:
            im_copy = im_copy.multiply(ee.Number(sd.get(band))).add(ee.Number(mean.get(band)))
        else:
            im_copy = im_copy.add(ee.Number(mean.get(band)))

        img = img.addBands(im_copy, overwrite=True)
    return img
