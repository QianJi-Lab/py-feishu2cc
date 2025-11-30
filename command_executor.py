"""
命令执行器 - Python 实现
对应 Go 版本: internal/command/executor.go
"""

import subprocess 
import logging 
from typing import Optional 
from dataclasses import dataclass 
from datetime import datetime 

logger =logging .getLogger (__name__ )




@dataclass 
class CommandResult :

    token :str 
    command :str 
    success :bool 
    method :str 
    output :str =""
    error :str =""
    exec_time_ms :int =0 
    timestamp :datetime =None 

    def __post_init__ (self ):
        if self .timestamp is None :
            self .timestamp =datetime .now ()




class TmuxCommandExecutor :


    def __init__ (self ,session_manager ):
        self .session_manager =session_manager 

    def execute_command (
    self ,
    token :str ,
    command :str ,
    user_id :str 
    )->CommandResult :

        start_time =datetime .now ()


        session =self .session_manager .validate_session (token )
        if session is None :
            return CommandResult (
            token =token ,
            command =command ,
            success =False ,
            method ="failed",
            error ="Session validation failed",
            exec_time_ms =self ._calc_exec_time (start_time )
            )


        if not self ._validate_command (command ):
            return CommandResult (
            token =token ,
            command =command ,
            success =False ,
            method ="failed",
            error ="Command validation failed",
            exec_time_ms =self ._calc_exec_time (start_time )
            )


        clean_command =self ._sanitize_command (command )


        result =self ._execute_in_tmux (session .tmux_session ,clean_command )
        result .token =token 
        result .command =command 
        result .exec_time_ms =self ._calc_exec_time (start_time )


        self .session_manager .update_session (token )

        logger .info (
        f"Command execution completed: token={token }, "
        f"success={result .success }, method={result .method }"
        )

        return result 

    def _execute_in_tmux (
    self ,
    session_name :str ,
    command :str 
    )->CommandResult :

        logger .info (f"Executing in tmux session '{session_name }': {command }")


        if not self ._tmux_session_exists (session_name ):
            return CommandResult (
            token ="",
            command =command ,
            success =False ,
            method ="failed",
            error =f"Tmux session '{session_name }' does not exist"
            )


        try :
            result =subprocess .run (
            ["tmux","send-keys","-t",session_name ,command ,"Enter"],
            capture_output =True ,
            text =True ,
            timeout =30 
            )

            if result .returncode ==0 :
                return CommandResult (
                token ="",
                command =command ,
                success =True ,
                method ="tmux",
                output ="Command sent to tmux session successfully"
                )
            else :
                logger .warning (
                f"tmux send-keys failed: {result .stderr }"
                )

                return self ._fallback_execution (session_name ,command )

        except subprocess .TimeoutExpired :
            return CommandResult (
            token ="",
            command =command ,
            success =False ,
            method ="failed",
            error ="Command execution timeout"
            )
        except Exception as e :
            logger .error (f"Failed to execute command: {e }")
            return CommandResult (
            token ="",
            command =command ,
            success =False ,
            method ="failed",
            error =str (e )
            )

    def _fallback_execution (
    self ,
    session_name :str ,
    command :str 
    )->CommandResult :

        logger .info (f"Attempting fallback execution for session {session_name }")


        try :
            result =subprocess .run (
            ["tmux","new-window","-t",session_name ,"-n","claude-cmd",command ],
            capture_output =True ,
            text =True ,
            timeout =30 
            )

            if result .returncode ==0 :
                return CommandResult (
                token ="",
                command =command ,
                success =True ,
                method ="fallback",
                output ="Command executed in new tmux window"
                )
        except Exception as e :
            logger .warning (f"Fallback method 1 failed: {e }")


        try :
            result =subprocess .run (
            ["tmux","send","-t",session_name ,command ,"C-m"],
            capture_output =True ,
            text =True ,
            timeout =30 
            )

            if result .returncode ==0 :
                return CommandResult (
                token ="",
                command =command ,
                success =True ,
                method ="fallback",
                output ="Command sent using alternative method"
                )
        except Exception as e :
            logger .warning (f"Fallback method 2 failed: {e }")


        return CommandResult (
        token ="",
        command =command ,
        success =False ,
        method ="failed",
        error ="All execution methods failed"
        )

    def _tmux_session_exists (self ,session_name :str )->bool :

        try :
            result =subprocess .run (
            ["tmux","has-session","-t",session_name ],
            capture_output =True ,
            timeout =10 
            )
            return result .returncode ==0 
        except Exception as e :
            logger .error (f"Failed to check tmux session: {e }")
            return False 

    def _validate_command (self ,command :str )->bool :

        if not command or not command .strip ():
            return False 


        dangerous_commands =[
        "rm -rf /",
        "mkfs",
        "dd if=/dev/zero",
        "> /dev/sda",
        "fork bomb",
        ":(){ :|:& };:"
        ]

        command_lower =command .lower ()
        for dangerous in dangerous_commands :
            if dangerous in command_lower :
                logger .warning (f"Blocked dangerous command: {command }")
                return False 

        return True 

    def _sanitize_command (self ,command :str )->str :


        command =command .strip ()




        return command 

    def _calc_exec_time (self ,start_time :datetime )->int :

        delta =datetime .now ()-start_time 
        return int (delta .total_seconds ()*1000 )




class CommandParser :


    @staticmethod 
    def parse_remote_command (message :str )->Optional [tuple [str ,str ]]:

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




if __name__ =='__main__':

    logging .basicConfig (
    level =logging .INFO ,
    format ='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


    class MockSessionManager :
        def validate_session (self ,token ):
            from dataclasses import dataclass 
            @dataclass 
            class MockSession :
                token :str 
                tmux_session :str ="claude-code"

            return MockSession (token =token )

        def update_session (self ,token ):
            pass 


    executor =TmuxCommandExecutor (MockSessionManager ())


    parser =CommandParser ()
    parsed =parser .parse_remote_command ("ABC12345: ls -la")
    if parsed :
        token ,command =parsed 
        print (f"Parsed: token={token }, command={command }")




