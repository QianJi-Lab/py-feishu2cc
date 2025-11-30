"""
命令验证器
"""

import logging 

logger =logging .getLogger (__name__ )


class CommandValidator :



    DANGEROUS_COMMANDS =[
    "rm -rf /",
    "mkfs",
    "dd if=/dev/zero",
    "> /dev/sda",
    "fork bomb",
    ":(){ :|:& };:"
    ]

    def validate_command (self ,command :str )->bool :

        if not command or not command .strip ():
            return False 

        command_lower =command .lower ()
        for dangerous in self .DANGEROUS_COMMANDS :
            if dangerous in command_lower :
                logger .warning (f"Blocked dangerous command: {command }")
                return False 

        return True 

    def validate_user (self ,user_id :str )->bool :


        return True 
