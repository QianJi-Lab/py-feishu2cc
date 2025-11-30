"""
Session 文件存储
"""

import json 
import logging 
from pathlib import Path 
from typing import Dict 
from datetime import datetime 

from .types import Session 

logger =logging .getLogger (__name__ )


class FileStorage :


    def __init__ (self ,file_path :str ):
        self .file_path =Path (file_path )
        self .file_path .parent .mkdir (parents =True ,exist_ok =True )

    def load (self )->Dict [str ,Session ]:

        if not self .file_path .exists ():
            return {}

        try :
            data =json .loads (self .file_path .read_text (encoding ='utf-8'))
            sessions ={}
            for token ,sess_data in data .get ('sessions',{}).items ():
                try :
                    sessions [token ]=Session .from_dict (sess_data )
                except Exception as e :
                    logger .error (f"Failed to load session {token }: {e }")
            return sessions 
        except Exception as e :
            logger .error (f"Failed to load sessions from {self .file_path }: {e }")
            return {}

    def save (self ,sessions :Dict [str ,Session ])->None :

        data ={
        'sessions':{token :sess .to_dict ()for token ,sess in sessions .items ()},
        'updated_at':datetime .now ().isoformat ()
        }
        self .file_path .write_text (
        json .dumps (data ,indent =2 ,ensure_ascii =False ),
        encoding ='utf-8'
        )
