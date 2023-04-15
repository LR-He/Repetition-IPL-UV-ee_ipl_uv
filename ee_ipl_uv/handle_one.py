import ee
from ee_ipl_uv import image_wrapper
from ee_ipl_uv import multitemporal_cloud_masking
from ee_ipl_uv import converters
from ee_ipl_uv import normalization
from ee_ipl_uv import clustering

# 根据index获取输入图像
def getImagePredictClouds(image_collection_name,img_index):
    return ee.Image(image_collection_name+'/'+img_index)


# 根据index获取img_wrap
def getImgWrap(image_index,image_collection_name):
    return image_wrapper.L8L1TImage(image_index,image_collection_name)


# 根据输入的原始有云图片寻找前一段时间的所有图像
def getImgColl(image_wrap,region_of_interest=None,NUMBER_IMAGES=30):
    imgcoll = multitemporal_cloud_masking.PreviousImagesWithCC(image_wrap,region_of_interest=None,NUMBER_IMAGES=30)
    featurecol = converters.eeImageCollectionToPandas(imgcoll,["system:time_start","CC","system:index"])
    return imgcoll, featurecol

# # 获取背景图像和差异图像
# def getBackgroundAndDiff(img_index,image_collection_name,region_of_interest=None,NUMBER_IMAGES=30):
 

# 处理一张图片的过程
def processingOne(img_index,image_collection_name,region_of_interest=None,NUMBER_IMAGES=30):
    
    image_predict_clouds = ee.Image(image_collection_name+'/'+img_index)

    # 根据index获取img_wrap
    image_wrap  = image_wrapper.L8L1TImage(img_index,image_collection_name)

    # 根据输入的原始有云图片寻找前一段时间的所有图像
    imgcoll = multitemporal_cloud_masking.PreviousImagesWithCC(image_wrap,region_of_interest=None,NUMBER_IMAGES=30)
    featurecol = converters.eeImageCollectionToPandas(imgcoll,["system:time_start","CC","system:index"])

    # 根据“CC”筛选出云量少于 5 的最少云的 3 张“无云”图像
    max_lags = 3 
    image_with_lags = multitemporal_cloud_masking.SelectImagesTraining(image_wrap,
                                        region_of_interest=region_of_interest,
                                        num_images=max_lags,
                                        threshold_cc=5)
    print(image_with_lags.getInfo())
    
    # 使用 3 张“无云”图像通过中值滤波器计算出背景图
    reflectance_bands_landsat8 = image_wrap.reflectance_bands()
    img_percentile = multitemporal_cloud_masking.PredictPercentile(image_wrap, region_of_interest, num_images=3,
                                           threshold_cc=5)
    reflectance_bands_landsat8_perc50 = [i + "_p50" for i in image_wrap.reflectance_bands()]
    background_prediction = img_percentile.select(reflectance_bands_landsat8_perc50)
    
    # 获取差异图像（输入的原始有云图像 - 估计的背景图像）
    image_to_predict =image_with_lags.select(reflectance_bands_landsat8)
    img_differences = image_to_predict.subtract(background_prediction)
#     return background_prediction,img_differences


# # 聚类差异图像
# def clusterDiff(img_differences,region_of_interest,reflectance_bands_landsat8):
    # 将差异图像可视标准化
    diff_norm_vis = img_differences.select(["B4","B3","B2"]).multiply(img_differences.select(["B4","B3","B2"])).reduce(ee.Reducer.mean())

    # 对差异图像进行聚类
    # 使用 K 平均聚类算法来处理所有的 Landsat-8 波段的差异图像，聚类数量为 10 。
    nClusters = 10
    numPixels = 600
    training = img_differences.sample(region=region_of_interest, scale=30, numPixels= numPixels)
    training, media, std = normalization.ComputeNormalizationFeatureCollection(training, 
                                                                            reflectance_bands_landsat8)
    clusterer = ee.Clusterer.wekaKMeans(nClusters).train(training)
    img_differences_normalized = normalization.ApplyNormalizationImage(img_differences,
                                                                    reflectance_bands_landsat8,
                                                                    media,std)
    result = img_differences_normalized.cluster(clusterer)

    # 对聚类结果根据阈值划分为云
    multitemporal_cloud_score,reflectance_score  = clustering.SelectClusters(image_to_predict,background_prediction,
                                                                         result,n_clusters=nClusters,
                                                                         region_of_interest=region_of_interest)
    
    # 获取云掩膜
    color_sequence = [  '1f77b4', 'ff7f0e', '2ca02c', 'd62728',
                        '9467bd', '8c564b', 'e377c2', '7f7f7f',
                        'bcbd22', '17becf']
    THRESHOLD_DIFFERENCE = 4000   # .04 
    THRESHOLD_REFLECTANCE = 17500   #.175
    cloud_score_threshold_original = multitemporal_cloud_score.gt(THRESHOLD_DIFFERENCE).multiply(reflectance_score.gt(THRESHOLD_REFLECTANCE))
    
    # 对云掩膜进行云边缘柔化
    cloud_score_threshold_original_radius = cloud_score_threshold_original.reduceNeighborhood(ee.Reducer.max(),ee.Kernel.circle(radius=3))
    cloud_score_threshold_radius = cloud_score_threshold_original_radius.updateMask(cloud_score_threshold_original_radius)
    cloud_score_threshold_radius_vis = cloud_score_threshold_radius.visualize(max=1,min=0,palette=color_sequence[:2])  # color_sequence[:2] = ['1f77b4', 'ff7f0e']
    
    # 将划分好的云覆盖在原始图像上
    imageRGB = image_predict_clouds.visualize(max=30000,bands=["B4","B3","B2"])
    mosaic_radius = ee.ImageCollection.fromImages([imageRGB, cloud_score_threshold_radius_vis]).mosaic()

    # 原始输入的有云图像删除云的部分：
    img_without_cloud_radius = imageRGB.multiply(cloud_score_threshold_original_radius.eq(0))

    # 对原始估计出的背景图做了除以 100 的调整
    background_prediction_adjust = background_prediction.select("B4_p50","B3_p50","B2_p50").clip(region_of_interest).divide(100)
    
    # 根据调整后的背景图填充到已经删除云的原始输入图像中，得到填补好的的无云图像。
    img_regain_radius = img_without_cloud_radius.select("vis-red","vis-green","vis-blue").clip(region_of_interest).where(img_without_cloud_radius.select("vis-red","vis-green","vis-blue").clip(region_of_interest).Not(),background_prediction_adjust.select("B4_p50","B3_p50","B2_p50"))
    
    # 返回：
    #   image_predict_clouds：原始有云图像
    #   imgcoll：当前图片前的所有图像
    #   featurecol：与当前图片前的所有图像对应的“CC”数据
    #   image_with_lags：筛选出的用于背景估计的 3 张无云图像
    #   background_prediction：原始估计出的背景图
    #   img_differences：差异图像
    #   diff_norm_vis：差异图可视标准化
    #   result：差异图像聚类结果
    #   multitemporal_cloud_score：云阈值结果
    #   reflectance_score：反射阈值结果
    #   mosaic_radius：云覆盖图
    #   img_without_cloud_radius：云删除图像
    #   img_regain_radius：云填补图像
    return (image_predict_clouds,imgcoll,featurecol,image_with_lags,background_prediction,
            img_differences,diff_norm_vis,result,multitemporal_cloud_score,reflectance_score,
            mosaic_radius,img_without_cloud_radius,img_regain_radius)


    

