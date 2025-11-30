"""
命令解析器
"""

from typing import Optional ,Tuple 


class CommandParser :


    @staticmethod 
    def parse_remote_command (message :str )->Optional [Tuple [str ,str ]]:

        if ':'not in message :
            return None 

        parts =message .split (':',1 )
        if len (parts )!=2 :
            return None 

        token =parts [0 ].strip ()
        command =parts [1 ].strip ()

        if not token or not command :
            return None 

        return (token ,command )
