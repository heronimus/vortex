import cv2
import numpy as np

from pathlib import Path
from collections import namedtuple, OrderedDict
from typing import Union, List, Dict, Tuple, Any

class BaseRuntime:
    """
    Standardized runtime class;
    the following signature are enforced :
    ```
        __call__ (input : np.ndarray, score_threshold : np.ndarray) -> np.ndarray
    ```
    """
    call_signature = {
        'return' : np.ndarray,
    }
    def __init__(self, input_specs : OrderedDict, output_name : Union[List[str],str], output_format : Dict[str,Dict[str,np.ndarray]], class_names : List[str]) :
        if isinstance(output_name, str) :
            self.output_name = [output_name]
        elif isinstance(output_name, list) :
            if not len(output_name) :
                raise ValueError("output_name can't be empty!")
            self.output_name = output_name
        else :
            raise RuntimeError("expects output_name is list or string, got %s" %type(output_name))
        ## enforce __call__ signature to subclass
        annotations = self.predict.__annotations__
        for key, value in BaseRuntime.call_signature.items() :
            if not key in annotations.keys() : 
                raise TypeError("missing annotation(s) : %s" %key)
            if value != annotations[key] :
                raise TypeError("type mismatch for %s, expects %s got %s" %(key, value, annotations[key]))
        self.output_format = output_format
        assert all(isinstance(value, dict) \
            and 'indices' in value and 'axis' in value \
                for key, value in self.output_format.items()
        )
        output_fields = sorted(self.output_format.keys())
        self.result_type = namedtuple('Result', [*output_fields])
        assert len(input_specs), "input specs can't be empty"
        assert all(isinstance(spec, (OrderedDict,dict)) and \
            'shape' in spec and 'type' in spec and \
                isinstance(spec['shape'],(tuple,list)) and \
                    isinstance(spec['type'],str)
                        for name, spec in input_specs.items()
        )
        self.input_specs = input_specs
        assert all(isinstance(name, str) for name in class_names)
        self.class_names = class_names

    def predict(self, *args, **kwargs):
        raise NotImplementedError
    
    @staticmethod
    def is_available() :
        raise NotImplementedError
    
    @staticmethod
    def resize_stretch(image : np.ndarray, size : Tuple[int,int]) :
        return cv2.resize(image, size)
    
    ## TODO : implement resize pad
    # @staticmethod
    # def resize_pad(image : np.ndarray, size : Tuple[int,int]) :
    #     return image

    @staticmethod
    def resize_batch(images : List[np.ndarray], size : Tuple[int,int,int,int], resize_kind='stretch') :
        """
        helper function to resize list of 
        np.ndarray (of possibly different size) 
        to single np array of same size
        """
        assert resize_kind in ['stretch'] and len(size)==4
        n, h, w, c = size if size[-1]==3 else tuple(size[i] for i in [0,3,1,2])
        resize = lambda x: BaseRuntime.resize_stretch(x, (h,w))
        dtype = images[0].dtype
        n_pad = n - len(images)
        batch_pad = [np.zeros((h,w,c),dtype=dtype)] * n_pad
        batch_image = list(map(resize, images))
        batch_image = batch_image + batch_pad
        return np.stack(batch_image)

    def __call__(self, *args, **kwargs):
        outputs = self.predict(*args, **kwargs)
        results = []
        for output in outputs:
            result = {
                key: np.take(
                    output, axis=int(fmt['axis']),
                    indices=fmt['indices'],
                ) if all(output.shape) else None 
                for key, fmt in self.output_format.items()
            }
            result = self.result_type(**result)
            results.append(result)
        return results
