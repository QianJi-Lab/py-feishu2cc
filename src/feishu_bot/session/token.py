"""
令牌生成器
"""

import random 
from typing import Set 


class TokenGenerator :


    def __init__ (self ,length :int =8 ):
        self .length =length 

        self .charset ="ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

    def generate (self )->str :

        return ''.join (random .choices (self .charset ,k =self .length ))

    def validate (self ,token :str )->bool :

        if len (token )!=self .length :
            return False 
        return all (c in self .charset for c in token )


def generate_unique_token (
generator :TokenGenerator ,
existing_tokens :Set [str ],
max_attempts :int =100 
)->str :

    for _ in range (max_attempts ):
        token =generator .generate ()
        if token not in existing_tokens :
            return token 
    raise RuntimeError (f"Failed to generate unique token after {max_attempts } attempts")
