# Claude Code Notification Hook
# 这个脚本会在 Claude Code 发送通知时被调用
# 根据 Claude Code 文档，Notification hook 会接收 JSON 格式的输入

# 调试日志
$debugLog = "C:\Users\23189\Desktop\py-feishu2cc\hook_debug.log"
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
"\n[$timestamp] Hook script executed" | Out-File -FilePath $debugLog -Append

# 记录所有环境变量
"Environment variables:" | Out-File -FilePath $debugLog -Append
Get-ChildItem env: | ForEach-Object { "  $($_.Name) = $($_.Value)" } | Out-File -FilePath $debugLog -Append

# 读取 Claude Code 传入的 JSON 数据 (从标准输入)
$inputJson = $input | Out-String
$claudeNotification = $null

"STDIN input: '$inputJson'" | Out-File -FilePath $debugLog -Append

if ($inputJson -and $inputJson.Trim() -ne "") {
    try {
        $claudeNotification = $inputJson | ConvertFrom-Json
        "Parsed JSON successfully" | Out-File -FilePath $debugLog -Append
        "Full JSON object: $($claudeNotification | ConvertTo-Json -Depth 10)" | Out-File -FilePath $debugLog -Append
    } catch {
        "Failed to parse JSON: $_" | Out-File -FilePath $debugLog -Append
        Write-Host "⚠️ Failed to parse Claude Code input JSON: $_" -ForegroundColor Yellow
    }
} else {
    "No STDIN input received" | Out-File -FilePath $debugLog -Append
}

# 获取当前目录和项目名称
$workingDir = Get-Location | Select-Object -ExpandProperty Path
$projectName = Split-Path -Leaf $workingDir

Add-Content -Path $debugLog -Value "Working dir: $workingDir"
Add-Content -Path $debugLog -Value "Project: $projectName"

# 提取通知消息和类型
$notificationMessage = ""
$notificationType = ""

if ($claudeNotification) {
    # 获取 hook 事件类型
    $hookEvent = if ($claudeNotification.hook_event_name) { $claudeNotification.hook_event_name } else { "unknown" }
    $notificationType = $hookEvent
    
    "Hook event: $hookEvent" | Out-File -FilePath $debugLog -Append
    
    # 尝试从 transcript 文件读取 Claude 的最后回复
    $transcriptPath = $claudeNotification.transcript_path
    if ($transcriptPath -and (Test-Path $transcriptPath)) {
        "Reading transcript from: $transcriptPath" | Out-File -FilePath $debugLog -Append
        
        try {
            # 读取 JSONL 文件的所有行（每行可能很长）
            $lines = Get-Content -Path $transcriptPath -ErrorAction Stop
            
            "Total lines in transcript: $($lines.Count)" | Out-File -FilePath $debugLog -Append
            
            # 查找最后一个 assistant 的回复
            $assistantMessage = ""
            for ($i = $lines.Count - 1; $i -ge 0; $i--) {
                try {
                    $line = $lines[$i] | ConvertFrom-Json
                    
                    # 记录每行的类型以便调试
                    "Line $i type: $($line.type)" | Out-File -FilePath $debugLog -Append
                    
                    # Claude Code 的 transcript 格式：{ type: "assistant", message: { role: "assistant", content: [...] } }
                    if ($line.type -eq "assistant" -and $line.message) {
                        $message = $line.message
                        
                        # content 是一个数组，需要提取 text 字段
                        if ($message.content -is [Array]) {
                            $textParts = @()
                            foreach ($contentItem in $message.content) {
                                if ($contentItem.type -eq "text" -and $contentItem.text) {
                                    $textParts += $contentItem.text
                                }
                            }
                            if ($textParts.Count -gt 0) {
                                $assistantMessage = $textParts -join "\n"
                            }
                        } elseif ($message.content) {
                            # 如果 content 是字符串（兼容其他格式）
                            $assistantMessage = $message.content
                        }
                        
                        if ($assistantMessage) {
                            "Found assistant message in line $i" | Out-File -FilePath $debugLog -Append
                            break
                        }
                    }
                    # 也尝试简单格式（兼容）
                    elseif ($line.role -eq "assistant" -and $line.content) {
                        $assistantMessage = $line.content
                        "Found assistant message (simple format) in line $i" | Out-File -FilePath $debugLog -Append
                        break
                    }
                } catch {
                    # 跳过无法解析的行
                    $errorMsg = $_.Exception.Message
                    "Failed to parse line $i : $errorMsg" | Out-File -FilePath $debugLog -Append
                    continue
                }
            }
            
            if ($assistantMessage) {
                $notificationMessage = $assistantMessage
                "Successfully extracted assistant message (${assistantMessage.Length} chars)" | Out-File -FilePath $debugLog -Append
                "Message preview: $($assistantMessage.Substring(0, [Math]::Min(100, $assistantMessage.Length)))" | Out-File -FilePath $debugLog -Append
            } else {
                "No assistant message found in transcript" | Out-File -FilePath $debugLog -Append
            }
            
        } catch {
            $errorMsg = $_.Exception.Message
            "Failed to read transcript: $errorMsg" | Out-File -FilePath $debugLog -Append
        }
    } else {
        "No transcript path found or file does not exist" | Out-File -FilePath $debugLog -Append
    }
    
    # 如果从 transcript 没有获取到内容，尝试从 JSON 字段获取
    if (-not $notificationMessage) {
        # PowerShell 5.1 兼容写法
        if ($claudeNotification.message) {
            $notificationMessage = $claudeNotification.message
        } elseif ($claudeNotification.content) {
            $notificationMessage = $claudeNotification.content
        } elseif ($claudeNotification.text) {
            $notificationMessage = $claudeNotification.text
        } elseif ($claudeNotification.response) {
            $notificationMessage = $claudeNotification.response
        } elseif ($claudeNotification.output) {
            $notificationMessage = $claudeNotification.output
        } elseif ($claudeNotification.reply) {
            $notificationMessage = $claudeNotification.reply
        } elseif ($claudeNotification.body) {
            $notificationMessage = $claudeNotification.body
        } else {
            $notificationMessage = ""
        }
        
        if ($notificationMessage) {
            "Extracted message from JSON fields" | Out-File -FilePath $debugLog -Append
        }
    }
    
    # 记录详细的字段信息用于调试
    "Final message length: $($notificationMessage.Length)" | Out-File -FilePath $debugLog -Append
    "Final type: $notificationType" | Out-File -FilePath $debugLog -Append
    
    Write-Host "🔔 Received Claude Code notification:" -ForegroundColor Cyan
    Write-Host "  Event: $hookEvent" -ForegroundColor Gray
    if ($notificationMessage) {
        $preview = if ($notificationMessage.Length -gt 200) { 
            $notificationMessage.Substring(0, 200) + "..." 
        } else { 
            $notificationMessage 
        }
        Write-Host "  Message Preview: $preview" -ForegroundColor Gray
        Write-Host "  Message Length: $($notificationMessage.Length) chars" -ForegroundColor Gray
    } else {
        Write-Host "  ⚠️ No message content found" -ForegroundColor Yellow
    }
}

# 构建 JSON 请求体
$body = @{
    type = "completed"
    user_id = "78495dd8"
    open_id = "ou_94f57fde84ec51561745ae6bc13ec6f8"
    project_name = $projectName
    tmux_session = "claude-code"
    working_dir = $workingDir
    description = "Claude Code task completed"
    task_output = $notificationMessage
} | ConvertTo-Json -Compress

# 发送通知
try {
    $response = Invoke-RestMethod -Uri "http://localhost:8080/webhook/notification" `
        -Method Post `
        -Body $body `
        -ContentType "application/json" `
        -ErrorAction Stop
    
    Write-Host "✅ Notification sent successfully. Token: $($response.token)"
    exit 0
} catch {
    Write-Error "❌ Failed to send notification: $_"
    exit 1
}
