"""
Session 数据模型
"""

from dataclasses import dataclass ,field ,asdict 
from datetime import datetime 
from typing import Optional 


@dataclass 
class Session :

    token :str 
    user_id :str 
    open_id :str 
    tmux_session :str 
    working_dir :str =""
    description :str =""
    status :str ="active"
    created_at :datetime =field (default_factory =datetime .now )
    expires_at :Optional [datetime ]=None 
    last_active_at :Optional [datetime ]=None 

    def to_dict (self )->dict :

        data =asdict (self )

        for key in ['created_at','expires_at','last_active_at']:
            if data [key ]and isinstance (data [key ],datetime ):
                data [key ]=data [key ].isoformat ()
        return data 

    @classmethod 
    def from_dict (cls ,data :dict )->'Session':


        for key in ['created_at','expires_at','last_active_at']:
            if data .get (key )and isinstance (data [key ],str ):
                data [key ]=datetime .fromisoformat (data [key ])
        return cls (**data )

    def is_expired (self )->bool :

        if self .expires_at is None :
            return False 
        return datetime .now ()>self .expires_at 


@dataclass 
class SessionConfig :

    token_length :int =8 
    expiration_hours :int =24 
    cleanup_interval_minutes :int =60 



STATUS_ACTIVE ="active"
STATUS_WAITING ="waiting"
STATUS_COMPLETED ="completed"
