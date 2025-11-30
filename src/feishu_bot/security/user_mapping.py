"""
用户ID映射服务
"""

import yaml 
import logging 
from pathlib import Path 
from typing import Dict ,Optional ,List 

logger =logging .getLogger (__name__ )


class UserMappingService :


    def __init__ (self ,whitelist_path :str ="configs/security/whitelist.yaml"):
        self .whitelist_path =Path (whitelist_path )
        self .users :Dict [str ,dict ]={}
        self .admin_users :List [str ]=[]
        self .global_limits :dict ={}
        self ._load_whitelist ()

    def _load_whitelist (self ):

        if not self .whitelist_path .exists ():
            logger .warning (f"Whitelist file not found: {self .whitelist_path }")
            return 

        try :
            with open (self .whitelist_path ,'r',encoding ='utf-8')as f :
                data =yaml .safe_load (f )or {}


            for user in data .get ('allowed_users',[]):
                user_id =user .get ('user_id')
                open_id =user .get ('open_id')
                if user_id and open_id :
                    self .users [user_id ]={
                    'user_id':user_id ,
                    'open_id':open_id ,
                    'name':user .get ('name',''),
                    'permissions':user .get ('permissions',[]),
                    'max_sessions':user .get ('max_sessions',5 )
                    }


            self .admin_users =data .get ('admin_users',[])


            self .global_limits =data .get ('global_limits',{})

            logger .info (f"Loaded {len (self .users )} users from whitelist")

        except Exception as e :
            logger .error (f"Failed to load whitelist: {e }")

    def resolve_open_id (self ,user_id :str ,open_id :str )->Optional [str ]:


        placeholders =['your_open_id','$FEISHU_OPEN_ID','FEISHU_OPEN_ID']

        if open_id in placeholders :
            if user_id in self .users :
                real_open_id =self .users [user_id ]['open_id']
                logger .info (f"Resolved placeholder OpenID for user {user_id }: {real_open_id }")
                return real_open_id 
            else :
                logger .warning (f"User {user_id } not found in whitelist")
                return None 


        return open_id 

    def get_user_info (self ,user_id :str )->Optional [dict ]:

        return self .users .get (user_id )

    def is_user_allowed (self ,user_id :str )->bool :

        return user_id in self .users 

    def is_admin (self ,open_id :str )->bool :

        return open_id in self .admin_users 

    def has_permission (self ,user_id :str ,permission :str )->bool :

        user =self .users .get (user_id )
        if not user :
            return False 


        if self .is_admin (user ['open_id']):
            return True 

        return permission in user .get ('permissions',[])

    def get_max_sessions (self ,user_id :str )->int :

        user =self .users .get (user_id )
        if not user :
            return 0 
        return user .get ('max_sessions',5 )

    def get_global_limit (self ,key :str ,default =None ):

        return self .global_limits .get (key ,default )
