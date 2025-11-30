"""
Session 管理器 - Python 实现
对应 Go 版本: internal/session/manager.go
"""

import json 
import threading 
from datetime import datetime ,timedelta 
from pathlib import Path 
from typing import Dict ,List ,Optional 
from dataclasses import dataclass ,field ,asdict 
import logging 

logger =logging .getLogger (__name__ )




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




class TokenGenerator :


    def __init__ (self ,length :int =8 ):
        self .length =length 

        self .charset ="ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

    def generate (self )->str :

        import random 
        return ''.join (random .choices (self .charset ,k =self .length ))

    def validate (self ,token :str )->bool :

        if len (token )!=self .length :
            return False 
        return all (c in self .charset for c in token )


def generate_unique_token (
generator :TokenGenerator ,
existing_tokens :set ,
max_attempts :int =100 
)->str :

    for _ in range (max_attempts ):
        token =generator .generate ()
        if token not in existing_tokens :
            return token 
    raise RuntimeError (f"Failed to generate unique token after {max_attempts } attempts")




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




class SessionManager :


    def __init__ (self ,storage_path :str ,config :SessionConfig ):
        self .storage =FileStorage (storage_path )
        self .config =config 
        self .generator =TokenGenerator (config .token_length )
        self .sessions :Dict [str ,Session ]={}
        self .lock =threading .RLock ()


        self ._load_sessions ()


        if config .cleanup_interval_minutes >0 :
            self ._start_cleanup_scheduler ()

    def _load_sessions (self )->None :

        try :
            self .sessions =self .storage .load ()
            logger .info (f"Loaded {len (self .sessions )} sessions from storage")
        except Exception as e :
            logger .error (f"Failed to load sessions: {e }")
            self .sessions ={}

    def _save_sessions (self )->None :

        try :
            self .storage .save (self .sessions )
        except Exception as e :
            logger .error (f"Failed to save sessions: {e }")

    def create_session (
    self ,
    user_id :str ,
    open_id :str ,
    tmux_session :str ,
    working_dir :str ="",
    description :str ="",
    status :str ="active"
    )->Session :

        with self .lock :

            existing_tokens =set (self .sessions .keys ())
            token =generate_unique_token (self .generator ,existing_tokens )


            now =datetime .now ()
            expires_at =now +timedelta (hours =self .config .expiration_hours )

            session =Session (
            token =token ,
            user_id =user_id ,
            open_id =open_id ,
            tmux_session =tmux_session ,
            working_dir =working_dir ,
            description =description ,
            status =status ,
            created_at =now ,
            expires_at =expires_at ,
            last_active_at =now 
            )


            self .sessions [token ]=session 


            self ._save_sessions ()

            logger .info (f"Created session: token={token }, user={user_id }")
            return session 

    def get_session (self ,token :str )->Optional [Session ]:

        with self .lock :
            session =self .sessions .get (token )
            if session is None :
                return None 


            if session .is_expired ():
                logger .warning (f"Session expired: {token }")
                return None 

            return session 

    def update_session (
    self ,
    token :str ,
    status :Optional [str ]=None ,
    description :Optional [str ]=None 
    )->Optional [Session ]:

        with self .lock :
            session =self .sessions .get (token )
            if session is None or session .is_expired ():
                return None 


            if status is not None :
                session .status =status 
            if description is not None :
                session .description =description 

            session .last_active_at =datetime .now ()


            self ._save_sessions ()

            logger .info (f"Updated session: {token }")
            return session 

    def delete_session (self ,token :str )->bool :

        with self .lock :
            if token not in self .sessions :
                return False 

            del self .sessions [token ]
            self ._save_sessions ()

            logger .info (f"Deleted session: {token }")
            return True 

    def list_sessions (self ,user_id :Optional [str ]=None )->List [Session ]:

        with self .lock :
            sessions =[]
            for session in self .sessions .values ():

                if session .is_expired ():
                    continue 


                if user_id is not None and session .user_id !=user_id :
                    continue 

                sessions .append (session )

            return sessions 

    def cleanup_expired_sessions (self )->int :

        with self .lock :
            tokens_to_delete =[]
            for token ,session in self .sessions .items ():
                if session .is_expired ():
                    tokens_to_delete .append (token )

            for token in tokens_to_delete :
                del self .sessions [token ]

            if tokens_to_delete :
                self ._save_sessions ()
                logger .info (f"Cleaned up {len (tokens_to_delete )} expired sessions")

            return len (tokens_to_delete )

    def validate_session (self ,token :str )->Optional [Session ]:


        if not self .generator .validate (token ):
            logger .warning (f"Invalid token format: {token }")
            return None 

        return self .get_session (token )

    def _start_cleanup_scheduler (self )->None :

        from apscheduler .schedulers .background import BackgroundScheduler 

        scheduler =BackgroundScheduler ()
        scheduler .add_job (
        self .cleanup_expired_sessions ,
        'interval',
        minutes =self .config .cleanup_interval_minutes 
        )
        scheduler .start ()
        logger .info (f"Started cleanup scheduler: interval={self .config .cleanup_interval_minutes }min")




if __name__ =='__main__':

    logging .basicConfig (
    level =logging .INFO ,
    format ='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


    config =SessionConfig (
    token_length =8 ,
    expiration_hours =24 ,
    cleanup_interval_minutes =60 
    )
    manager =SessionManager ('data/sessions.json',config )


    session =manager .create_session (
    user_id ='user123',
    open_id ='ou_abc123',
    tmux_session ='claude-code',
    working_dir ='/home/user/project',
    description ='Test project'
    )
    print (f"Created session: {session .token }")


    retrieved =manager .get_session (session .token )
    print (f"Retrieved session: {retrieved .token if retrieved else 'Not found'}")


    all_sessions =manager .list_sessions ()
    print (f"Total sessions: {len (all_sessions )}")


    manager .update_session (session .token ,status ='waiting')


    manager .delete_session (session .token )
