"""
命令执行器
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
        from .parser import CommandParser 
        from .validator import CommandValidator 
        self .parser =CommandParser ()
        self .validator =CommandValidator ()

    def execute_command (self ,token :str ,command :str ,user_id :str )->CommandResult :

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


        if not self .validator .validate_command (command ):
            return CommandResult (
            token =token ,
            command =command ,
            success =False ,
            method ="failed",
            error ="Command validation failed",
            exec_time_ms =self ._calc_exec_time (start_time )
            )


        result =self ._execute_in_tmux (session .tmux_session ,command )
        result .token =token 
        result .command =command 
        result .exec_time_ms =self ._calc_exec_time (start_time )


        self .session_manager .update_session (token )

        logger .info (f"Command executed: token={token }, success={result .success }")
        return result 

    def _execute_in_tmux (self ,session_name :str ,command :str )->CommandResult :

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

                output =self ._capture_tmux_output (session_name )

                return CommandResult (
                token ="",
                command =command ,
                success =True ,
                method ="tmux",
                output =output if output else "命令已发送到 tmux 会话"
                )
            else :
                return self ._fallback_execution (session_name ,command )
        except Exception as e :
            return CommandResult (
            token ="",
            command =command ,
            success =False ,
            method ="failed",
            error =str (e )
            )

    def _capture_tmux_output (self ,session_name :str ,lines :int =10 )->str :

        try :

            result =subprocess .run (
            ["tmux","capture-pane","-t",session_name ,"-p","-S",f"-{lines }"],
            capture_output =True ,
            text =True ,
            timeout =5 
            )

            if result .returncode ==0 and result .stdout :
                output =result .stdout .strip ()

                if len (output )>1000 :
                    output =output [-1000 :]+"\n...(output truncated)"
                return output 
        except Exception as e :
            logger .debug (f"Failed to capture tmux output: {e }")

        return ""

    def _fallback_execution (self ,session_name :str ,command :str )->CommandResult :

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
        except Exception :
            pass 

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
        except Exception :
            return False 

    def _calc_exec_time (self ,start_time :datetime )->int :

        delta =datetime .now ()-start_time 
        return int (delta .total_seconds ()*1000 )
