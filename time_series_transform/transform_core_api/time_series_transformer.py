import gc
import uuid
import warnings
import numpy as np
import pandas as pd
import pyarrow as pa
from pyarrow import parquet as pq
from collections import defaultdict
from time_series_transform import io
from time_series_transform.transform_core_api.base import *


class Time_Series_Transformer(object):

    def __init__(self,data,timeSeriesCol,mainCategoryCol):
        super().__init__()
        if isinstance(data,(Time_Series_Data,Time_Series_Data_Collection)):
            self.time_series_data = data
        else:
            self.time_series_data = self._setup_time_series_data(data,timeSeriesCol,mainCategoryCol)
        self.timeSeriesCol = timeSeriesCol
        self._isCollection = [True if mainCategoryCol is not None else False][0]
        self.mainCategoryCol = mainCategoryCol

    def _setup_time_series_data(self,data,timeSeriesCol,mainCategoryCol):
        if timeSeriesCol is None:
            raise KeyError("time series index is required")
        tsd = Time_Series_Data(data,timeSeriesCol)
        if mainCategoryCol is None:
            return tsd
        tsc = Time_Series_Data_Collection(tsd,timeSeriesCol,mainCategoryCol)
        return tsc
    
    def transform(self,inputLabels,newName,func,n_jobs =1,verbose = 0,backend='loky',*args,**kwargs):
        if isinstance(self.time_series_data,Time_Series_Data_Collection):
            self.time_series_data = self.time_series_data.transform(inputLabels,newName,func,n_jobs =1,verbose = 0,backend='loky',*args,**kwargs)
        else:
            self.time_series_data = self.time_series_data.transform(inputLabels,newName,func,*args,**kwargs)
        return self


    def _transform_wrapper(self,inputLabels,newName,func,suffix,suffixNum,inputAsList,n_jobs,verbose,*args,**kwargs):
        if isinstance(inputLabels,list) == False:
            inputLabels = [inputLabels]
        if self._isCollection:
            if inputAsList == False:
                for i in inputLabels:
                    labelName = [f'{i}{suffix}{str(suffixNum)}' if suffix is not None else f"{i}{str(suffixNum)}"][0]
                    self.time_series_data.transform(i,labelName,func,n_jobs =n_jobs,verbose = verbose,*args,**kwargs)
                return
            labelName = newName
            self.time_series_data.transform(inputLabels,labelName,func,n_jobs =n_jobs,verbose = verbose,*args,**kwargs)
        else:
            if inputAsList == False:
                for i in inputLabels:
                    labelName = [f'{i}{suffix}{str(suffixNum)}' if suffix is not None else f"{i}{str(suffixNum)}"][0]
                    self.time_series_data.transform(i,labelName,func,*args,**kwargs)
                return
            labelName = newName
            self.time_series_data.transform(inputLabels,labelName,func,*args,**kwargs)


    def make_lag(self,inputLabels,lagNum,suffix=None,fillMissing=np.nan,verbose=0,n_jobs=1):
        self._transform_wrapper(
            inputLabels,
            None,
            make_lag,
            suffix,
            lagNum,
            False,
            n_jobs,
            verbose,
            lagNum=lagNum,
            fillMissing=fillMissing
            )
        return self

    def make_lead(self,inputLabels,leadNum,suffix=None,fillMissing=np.nan,verbose=0,n_jobs=1):
        self._transform_wrapper(
            inputLabels,
            None,
            make_lead,
            suffix,
            leadNum,
            False,
            n_jobs,
            verbose,
            leadNum=leadNum,
            fillMissing=fillMissing
            )
        return self
                
    def make_lag_sequence(self,inputLabels,windowSize,lagNum,suffix=None,fillMissing=np.nan,verbose=0,n_jobs=1):
        self._transform_wrapper(
            inputLabels,
            None,
            make_lag_sequnece,
            suffix,
            windowSize,
            False,
            n_jobs,
            verbose,
            windowSize=windowSize,
            lagNum = lagNum,
            fillMissing=fillMissing
            )
        return self

    def make_lead_sequence(self,inputLabels,windowSize,leadNum,suffix=None,fillMissing=np.nan,verbose=0,n_jobs=1):
        self._transform_wrapper(
            inputLabels,
            None,
            lead_sequence,
            suffix,
            windowSize,
            False,
            n_jobs,
            verbose,
            windowSize=windowSize,
            leadNum=leadNum,
            fillMissing=fillMissing
            )
        return self

    def make_identical_sequence(self,inputLabels,windowSize,suffix=None,verbose=0,n_jobs=1):
        self._transform_wrapper(
            inputLabels,
            None,
            identity_window,
            suffix,
            windowSize,
            False,
            n_jobs,
            verbose,
            windowSize=windowSize
            )
        return self

    def make_stack_sequence(self,inputLabels,newName,axis =-1,verbose=0,n_jobs=1):
        self._transform_wrapper(
            inputLabels,
            newName,
            stack_sequence,
            None,
            '',
            True,
            n_jobs,
            verbose,
            axis =axis
            )
        return self


    def make_label(self,key,collectionKey=None):
        if self._isCollection:
            if collectionKey is None:
                for i in self.time_series_data:
                    data = self.time_series_data[i][:,[key]][key]
                    self.time_series_data[i].set_labels(key)
                    self.time_series_data[i].remove(key)
            else:
                data = self.time_series_data[collectionKey][:,[key]][key]
                self.time_series_data[collectionKey].set_labels(key)
                self.time_series_data[collectionKey].remove(key)
        else:
            data = self.time_series_data[:,[key]][key]
            self.time_series_data.set_labels(key)
            self.time_series_data.remove(key)
        return self

    def remove_different_category_time(self):
        if self._isCollection:
            self.time_series_data.remove_different_time_index()
        else:
            warnings.warn('Setup mainCategoryCol is necessary for this function')
        return self

    def pad_different_category_time(self,fillMissing= np.nan):
        if self._isCollection:
            self.time_series_data.pad_time_index(fillMissing)
        else:
            warnings.warn('Setup mainCategoryCol is necessary for this function')
        return self

    def remove_category(self,categoryName):
        if self._isCollection:
            self.time_series_data.remove(categoryName)
        return self

    def remove_feature(self,colName):
        if isinstance(self._isCollection):
            for i in self.time_series_data:
                self.time_series_data[i].remove(colName)
                return self
        self.time_series_data.remove(colName)
        return self

    @classmethod
    def from_pandas(cls, pandasFrame,timeSeriesCol,mainCategoryCol):
        data = io.from_pandas(pandasFrame,timeSeriesCol,mainCategoryCol)
        return cls(data,timeSeriesCol,mainCategoryCol)

    @classmethod
    def from_numpy(cls,numpyData,timeSeriesCol,mainCategoryCol):
        data = io.from_numpy(numpyData,timeSeriesCol,mainCategoryCol)
        return cls(data,timeSeriesCol,mainCategoryCol)

    def to_pandas(self,expandCategory=False,expandTime=False,preprocessType='ignore',sepLabel = False):
        if sepLabel == False:
            return io.to_pandas(
                self.time_series_data,
                expandCategory = expandCategory,
                expandTime = expandTime,
                preprocessType=preprocessType
                )
        

    def to_numpy(self,expandCategory=False,expandTime=False,preprocessType='ignore',sepLabel = False):
        if sepLabel == False:
            return io.to_numpy(self.time_series_data,expandCategory,expandTime,preprocessType)

    def to_dict(self):
        return self.time_series_data[:]

    def __eq__(self,other):
        if isinstance(other,Time_Series_Transformer):
            return self.time_series_data == other.time_series_data
        return False


    def __repr__(self):
        return super().__repr__()

def make_sequence(arr, window,fillMissing=np.nan):
    """
    rolling_window create an rolling window tensor
    
    this function create a rolling window numpy tensor given its original sequence and window size
    
    Parameters
    ----------
    arr : numpy 1D array
        the original data sequence
    window : int
        aggregation window size
    
    Returns
    -------
    numpy 2d array
        the rolling window array
    """
    shape = arr.shape[:-1] + (arr.shape[-1] - window + 1, window)
    strides = arr.strides + (arr.strides[-1],)
    seq = np.lib.stride_tricks.as_strided(arr, shape=shape, strides=strides)
    empty = np.empty(((len(arr)-seq.shape[0],seq.shape[1])))
    empty[:] = fillMissing
    res = np.vstack([empty,seq])
    return res


def make_lag_sequnece(data,windowSize,lagNum,fillMissing):
    lagdata = np.array(make_lag(data,lagNum,fillMissing))
    return make_sequence(lagdata,windowSize,fillMissing)

def identity_window(arr,windowSize):
    return np.repeat(arr,windowSize).reshape((-1,windowSize))

def make_lead(data,leadNum,fillMissing):
    res = np.empty((leadNum))
    res[:] = fillMissing
    res = res.tolist()        
    leadValues = data[leadNum:].tolist()
    leadValues.extend(res)        
    return leadValues        

def make_lag(data,lagNum,fillMissing):
    res = np.empty((lagNum))
    res[:] = fillMissing
    res = res.tolist()        
    lagValues = data[:-lagNum]
    res.extend(lagValues)        
    return res

def lead_sequence(arr,leadNum,windowSize,fillMissing=np.nan):
    shape = arr.shape[:-1] + (arr.shape[-1] - windowSize + 1, windowSize)
    strides = arr.strides + (arr.strides[-1],)
    seq = np.lib.stride_tricks.as_strided(arr, shape=shape, strides=strides)
    seq = seq[leadNum:]
    empty = np.empty(((len(arr)-seq.shape[0],seq.shape[1])))
    empty[:] = fillMissing
    res = np.vstack([seq,empty])
    return res

def stack_sequence(arrDict, axis = -1):
    res = None
    for ix, v in enumerate(arrDict):
        if ix == 0:
            res = arrDict[v]
            continue
        res = np.stack([res,arrDict[v]],axis = axis )
    return res