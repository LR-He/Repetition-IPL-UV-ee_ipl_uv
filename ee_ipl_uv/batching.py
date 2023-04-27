from datetime import datetime
from IPython.display import Image, display

#from ee_ipl_uv import multitemporal_cloud_masking
from ee_ipl_uv import download
from ee_ipl_uv import time_series_operations
from ee_ipl_uv import time_series_show
from ee_ipl_uv import predefined_cloud_algorithms
#from ee_ipl_uv import converters
#from ee_ipl_uv import image_wrapper

class Caption():
    num_figure = 1
    def __init__(self,s):
        self.s = s
        self.current_number = Caption.num_figure
        Caption.num_figure = Caption.num_figure+1 
    def _repr_html_(self):
        return '<center>Figure {0}. {1}</center>'.format(self.current_number,self.s)
        
imgcoll_org = ee.ImageCollection(image_collection_name).filterDate(start_date, end_date).filterBounds(region_of_interest).sort("system:time_start")
print(imgcoll_org.getInfo())
print(imgcoll_org.size().getInfo())
