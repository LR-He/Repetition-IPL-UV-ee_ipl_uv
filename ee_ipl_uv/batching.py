import ee
improt datetime

# from datetime import datetime
# from IPython.display import Image, display

#from ee_ipl_uv import multitemporal_cloud_masking
#from ee_ipl_uv import download
# from ee_ipl_uv import time_series_operations
# from ee_ipl_uv import time_series_show
# from ee_ipl_uv import predefined_cloud_algorithms
#from ee_ipl_uv import converters
#from ee_ipl_uv import image_wrapper

from ee_ipl_uv import handle_one

# 获取所有图片的 index 。
def getImgId(img):
  return ee.Image(img).id()

# 处理单个
def handleOne(img_index,image_collection_name,region_of_interest):
  return handle_one.processingOne(img_index,image_collection_name,region_of_interest=region_of_interest,NUMBER_IMAGES=30)

# 批量处理
def doBatching(image_collection_name, start_date, end_date, region_of_interest):
    imgcoll_org = ee.ImageCollection(image_collection_name).filterDate(start_date, end_date).filterBounds(region_of_interest).sort("system:time_start")
    # print(imgcoll_org.getInfo())
    # print(imgcoll_org.size().getInfo())

    img_list = imgcoll_org.toList(imgcoll_org.size())
    #print(img_list.getInfo())
    
    # 获取图像的 id ，得到的 id 类型为 ee.String 。
    imgid_list = img_list.map(getImgId)
    # print(imgid_list.getInfo())
    # print(type(imgid_list.get(0)))


    # 将id的类型从 ee.String 转为 str ，str 才能和 str 连接。
    img_index_list = []
    i = ee.Number(0)
    while i.lt(imgid_list.size()).getInfo():
      img_index = imgid_list.get(i).getInfo()
      img_index_list.append(img_index)
      i = i.add(1)
    #print(img_index_list)
    # print(img_index_list[0])   # LC08_122044_20220903
    # print(type(img_index_list[0]))  # <class 'str'>

    # 获取图片时间
    img_time_list = []
    for i in range(len(img_index_list)):
      img_time = datetime.datetime.utcfromtimestamp(ee.Image(img_list.get(i)).get("system:time_start").getInfo()/1000)
      img_time_list.append(img_time)
      
    # 循环处理
    result_dicts_list = []
    for index in img_index_list:
      result_dict = handleOne(index,image_collection_name,region_of_interest)
      result_dicts_list.append(result_dict)

    # print(result_dicts_list)
    # print(len(result_dicts_list))
    
    return imgcoll_org, img_time_list, result_dicts_list




