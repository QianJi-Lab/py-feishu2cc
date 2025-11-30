"""
Session 管理器
"""

import logging 
import threading 
from datetime import datetime ,timedelta 
from typing import Dict ,List ,Optional 

from .types import Session ,SessionConfig ,STATUS_ACTIVE 
from .storage import FileStorage 
from .token import TokenGenerator ,generate_unique_token 

logger =logging .getLogger (__name__ )


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
    status :str =STATUS_ACTIVE 
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

    def get_user_active_session (self ,open_id :str )->Optional [Session ]:

        with self .lock :
            user_sessions =[]

            for session in self .sessions .values ():

                if session .open_id ==open_id and not session .is_expired ():
                    user_sessions .append (session )

            if not user_sessions :
                return None 


            user_sessions .sort (key =lambda s :s .last_active_at ,reverse =True )

            most_recent =user_sessions [0 ]
            logger .info (f"Found active session for user {open_id }: token={most_recent .token }, tmux={most_recent .tmux_session }")
            return most_recent 

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
