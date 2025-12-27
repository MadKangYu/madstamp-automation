"""
Madstamp Automation - 이메일 핸들러 모듈

Gmail MCP를 통해 이메일을 모니터링하고 고객 요청을 처리합니다.
"""

import asyncio
import json
import logging
import os
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class EmailStatus(str, Enum):
    """이메일 처리 상태"""
    PENDING = "pending"
    ANALYZING = "analyzing"
    PRODUCIBLE = "producible"
    NEEDS_CLARIFICATION = "needs_clarification"
    NOT_PRODUCIBLE = "not_producible"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class EmailAttachment:
    """이메일 첨부파일"""
    filename: str
    mime_type: str
    size: int
    local_path: Optional[str] = None


@dataclass
class CustomerEmail:
    """고객 이메일"""
    message_id: str
    thread_id: str
    from_email: str
    from_name: str
    subject: str
    body: str
    received_at: datetime
    attachments: list[EmailAttachment] = field(default_factory=list)
    status: EmailStatus = EmailStatus.PENDING
    analysis_result: Optional[dict] = None


class GmailMCPClient:
    """
    Gmail MCP 클라이언트
    
    manus-mcp-cli를 통해 Gmail MCP 서버와 통신합니다.
    """

    def __init__(self, server_name: str = "gmail"):
        self.server_name = server_name
        self.download_dir = "/tmp/email_attachments"
        Path(self.download_dir).mkdir(parents=True, exist_ok=True)

    async def _run_mcp_command(self, tool_name: str, input_data: dict) -> dict:
        """MCP 명령 실행"""
        cmd = [
            "manus-mcp-cli",
            "tool",
            "call",
            tool_name,
            "--server", self.server_name,
            "--input", json.dumps(input_data),
        ]

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                logger.error(f"MCP command failed: {stderr.decode()}")
                return {"error": stderr.decode()}

            return json.loads(stdout.decode())

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse MCP response: {e}")
            return {"error": str(e), "raw": stdout.decode() if stdout else ""}
        except Exception as e:
            logger.error(f"MCP command error: {e}")
            return {"error": str(e)}

    async def list_tools(self) -> list[str]:
        """사용 가능한 도구 목록 조회"""
        cmd = [
            "manus-mcp-cli",
            "tool",
            "list",
            "--server", self.server_name,
        ]

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()
            return stdout.decode().strip().split("\n")
        except Exception as e:
            logger.error(f"Failed to list tools: {e}")
            return []

    async def search_emails(
        self,
        query: str = "is:unread",
        max_results: int = 10,
    ) -> list[dict]:
        """이메일 검색"""
        result = await self._run_mcp_command(
            "gmail_search",
            {"query": query, "maxResults": max_results},
        )
        
        if "error" in result:
            logger.error(f"Email search failed: {result['error']}")
            return []
        
        return result.get("messages", [])

    async def get_email(self, message_id: str) -> Optional[dict]:
        """이메일 상세 조회"""
        result = await self._run_mcp_command(
            "gmail_get_message",
            {"messageId": message_id},
        )
        
        if "error" in result:
            logger.error(f"Failed to get email: {result['error']}")
            return None
        
        return result

    async def download_attachment(
        self,
        message_id: str,
        attachment_id: str,
        filename: str,
    ) -> Optional[str]:
        """첨부파일 다운로드"""
        result = await self._run_mcp_command(
            "gmail_get_attachment",
            {
                "messageId": message_id,
                "attachmentId": attachment_id,
            },
        )
        
        if "error" in result:
            logger.error(f"Failed to download attachment: {result['error']}")
            return None
        
        # Base64 디코딩 및 저장
        import base64
        
        data = result.get("data", "")
        if data:
            local_path = os.path.join(self.download_dir, filename)
            with open(local_path, "wb") as f:
                f.write(base64.urlsafe_b64decode(data))
            return local_path
        
        return None

    async def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        attachments: list[str] = None,
        reply_to_message_id: Optional[str] = None,
    ) -> bool:
        """이메일 발송"""
        input_data = {
            "to": to,
            "subject": subject,
            "body": body,
        }
        
        if reply_to_message_id:
            input_data["replyToMessageId"] = reply_to_message_id
        
        if attachments:
            input_data["attachments"] = attachments
        
        result = await self._run_mcp_command("gmail_send", input_data)
        
        if "error" in result:
            logger.error(f"Failed to send email: {result['error']}")
            return False
        
        return True

    async def mark_as_read(self, message_id: str) -> bool:
        """이메일 읽음 처리"""
        result = await self._run_mcp_command(
            "gmail_modify_labels",
            {
                "messageId": message_id,
                "removeLabels": ["UNREAD"],
            },
        )
        
        return "error" not in result


class EmailHandler:
    """
    이메일 핸들러
    
    고객 이메일을 모니터링하고 도장 제작 요청을 처리합니다.
    """

    def __init__(
        self,
        target_email: str = "goopick@goopick.net",
        notification_email: str = "richardowen7212@gmail.com",
    ):
        self.target_email = target_email
        self.notification_email = notification_email
        self.gmail_client = GmailMCPClient()

    async def check_new_emails(
        self,
        label: str = "INBOX",
        unread_only: bool = True,
    ) -> list[CustomerEmail]:
        """새 이메일 확인"""
        query = f"in:{label}"
        if unread_only:
            query += " is:unread"
        
        # 도장 관련 키워드로 필터링
        keywords = ["도장", "스탬프", "stamp", "seal", "인장", "로고"]
        keyword_query = " OR ".join([f'"{kw}"' for kw in keywords])
        query += f" ({keyword_query})"

        messages = await self.gmail_client.search_emails(query=query)
        
        customer_emails = []
        for msg in messages:
            email_data = await self.gmail_client.get_email(msg.get("id", ""))
            if email_data:
                customer_email = self._parse_email(email_data)
                if customer_email:
                    customer_emails.append(customer_email)
        
        return customer_emails

    def _parse_email(self, email_data: dict) -> Optional[CustomerEmail]:
        """이메일 데이터 파싱"""
        try:
            headers = {h["name"]: h["value"] for h in email_data.get("payload", {}).get("headers", [])}
            
            # 발신자 파싱
            from_header = headers.get("From", "")
            from_match = re.match(r'"?([^"<]+)"?\s*<?([^>]+)>?', from_header)
            from_name = from_match.group(1).strip() if from_match else ""
            from_email = from_match.group(2).strip() if from_match else from_header
            
            # 본문 추출
            body = self._extract_body(email_data.get("payload", {}))
            
            # 첨부파일 추출
            attachments = self._extract_attachments(email_data.get("payload", {}))
            
            return CustomerEmail(
                message_id=email_data.get("id", ""),
                thread_id=email_data.get("threadId", ""),
                from_email=from_email,
                from_name=from_name,
                subject=headers.get("Subject", ""),
                body=body,
                received_at=datetime.fromtimestamp(
                    int(email_data.get("internalDate", 0)) / 1000
                ),
                attachments=attachments,
            )
        except Exception as e:
            logger.error(f"Failed to parse email: {e}")
            return None

    def _extract_body(self, payload: dict) -> str:
        """이메일 본문 추출"""
        import base64
        
        body = ""
        
        if "body" in payload and payload["body"].get("data"):
            body = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="ignore")
        elif "parts" in payload:
            for part in payload["parts"]:
                if part.get("mimeType") == "text/plain":
                    if part.get("body", {}).get("data"):
                        body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="ignore")
                        break
                elif part.get("mimeType") == "text/html" and not body:
                    if part.get("body", {}).get("data"):
                        html = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="ignore")
                        # HTML 태그 제거
                        body = re.sub(r'<[^>]+>', '', html)
        
        return body.strip()

    def _extract_attachments(self, payload: dict) -> list[EmailAttachment]:
        """첨부파일 정보 추출"""
        attachments = []
        
        def process_parts(parts):
            for part in parts:
                if part.get("filename") and part.get("body", {}).get("attachmentId"):
                    attachments.append(EmailAttachment(
                        filename=part["filename"],
                        mime_type=part.get("mimeType", "application/octet-stream"),
                        size=part.get("body", {}).get("size", 0),
                    ))
                if "parts" in part:
                    process_parts(part["parts"])
        
        if "parts" in payload:
            process_parts(payload["parts"])
        
        return attachments

    async def send_analysis_result(
        self,
        customer_email: CustomerEmail,
        analysis_result: dict,
    ) -> bool:
        """분석 결과 이메일 발송"""
        status = analysis_result.get("status", "unknown")
        
        if status == "producible":
            subject = f"Re: {customer_email.subject} - 도장 제작 가능합니다!"
            body = self._build_producible_email(customer_email, analysis_result)
        elif status == "needs_clarification":
            subject = f"Re: {customer_email.subject} - 추가 정보가 필요합니다"
            body = self._build_clarification_email(customer_email, analysis_result)
        else:
            subject = f"Re: {customer_email.subject} - 도장 제작 안내"
            body = self._build_not_producible_email(customer_email, analysis_result)
        
        return await self.gmail_client.send_email(
            to=customer_email.from_email,
            subject=subject,
            body=body,
            reply_to_message_id=customer_email.message_id,
        )

    def _build_producible_email(
        self,
        customer_email: CustomerEmail,
        analysis_result: dict,
    ) -> str:
        """제작 가능 이메일 본문 생성"""
        return f"""안녕하세요, {customer_email.from_name}님!

보내주신 이미지를 분석한 결과, 도장 제작이 가능합니다.

[분석 결과]
- 이미지 품질: {analysis_result.get('image_quality', 'N/A')}
- 감지된 요소: {', '.join(analysis_result.get('detected_elements', []))}
- 감지된 텍스트: {analysis_result.get('detected_text', 'N/A')}

[추천 폰트]
{self._format_font_recommendations(analysis_result.get('recommended_fonts', []))}

곧 도장 디자인 시안을 보내드리겠습니다.
추가 요청사항이 있으시면 회신해 주세요.

감사합니다.
GOOPICK 도장 제작팀

---
이 메일은 자동으로 생성되었습니다.
문의: goopick@goopick.net | +82 10 5911 2822
"""

    def _build_clarification_email(
        self,
        customer_email: CustomerEmail,
        analysis_result: dict,
    ) -> str:
        """확인 필요 이메일 본문 생성"""
        suggestions = analysis_result.get('suggestions', [])
        suggestions_text = '\n'.join([f"- {s}" for s in suggestions])
        
        return f"""안녕하세요, {customer_email.from_name}님!

보내주신 이미지를 분석한 결과, 추가 정보가 필요합니다.

[분석 결과]
- 판단 사유: {analysis_result.get('reason', 'N/A')}

[요청 사항]
{suggestions_text}

더 선명한 이미지나 추가 정보를 보내주시면 
빠르게 도장 제작을 진행해 드리겠습니다.

감사합니다.
GOOPICK 도장 제작팀

---
이 메일은 자동으로 생성되었습니다.
문의: goopick@goopick.net | +82 10 5911 2822
"""

    def _build_not_producible_email(
        self,
        customer_email: CustomerEmail,
        analysis_result: dict,
    ) -> str:
        """제작 불가 이메일 본문 생성"""
        return f"""안녕하세요, {customer_email.from_name}님!

보내주신 이미지를 분석한 결과, 
현재 상태로는 도장 제작이 어렵습니다.

[분석 결과]
- 판단 사유: {analysis_result.get('reason', 'N/A')}

[제안]
- 도장으로 제작하고자 하는 로고나 텍스트가 명확하게 보이는 이미지를 보내주세요.
- 손그림의 경우, 선이 명확하게 보이도록 스캔하거나 촬영해 주세요.
- 벡터 파일(AI, EPS, SVG)이 있다면 함께 보내주시면 더 좋습니다.

추가 문의사항이 있으시면 언제든 연락 주세요.

감사합니다.
GOOPICK 도장 제작팀

---
이 메일은 자동으로 생성되었습니다.
문의: goopick@goopick.net | +82 10 5911 2822
"""

    def _format_font_recommendations(self, fonts: list) -> str:
        """폰트 추천 포맷팅"""
        if not fonts:
            return "- 기본 폰트 사용 예정"
        
        lines = []
        for font in fonts[:3]:
            if isinstance(font, dict):
                lines.append(f"- {font.get('name', 'Unknown')} ({font.get('style', 'N/A')})")
            else:
                lines.append(f"- {font.name} ({font.style})")
        
        return '\n'.join(lines)

    async def send_completed_result(
        self,
        customer_email: CustomerEmail,
        generated_image_path: str,
        vector_files: list[str],
    ) -> bool:
        """완성된 도장 이미지 발송"""
        subject = f"Re: {customer_email.subject} - 도장 디자인이 완성되었습니다!"
        
        body = f"""안녕하세요, {customer_email.from_name}님!

요청하신 도장 디자인이 완성되었습니다.

첨부된 파일을 확인해 주세요:
- 미리보기 이미지 (PNG)
- 벡터 파일 (EPS/AI) - 인쇄용

수정이 필요하시면 말씀해 주세요.
만족하시면 결제 안내를 드리겠습니다.

감사합니다.
GOOPICK 도장 제작팀

---
이 메일은 자동으로 생성되었습니다.
문의: goopick@goopick.net | +82 10 5911 2822
"""
        
        attachments = [generated_image_path] + vector_files
        
        return await self.gmail_client.send_email(
            to=customer_email.from_email,
            subject=subject,
            body=body,
            attachments=attachments,
            reply_to_message_id=customer_email.message_id,
        )


async def monitor_emails_once(
    target_email: str = "goopick@goopick.net",
) -> list[CustomerEmail]:
    """
    이메일 모니터링 (1회)
    
    Args:
        target_email: 모니터링할 이메일 주소
        
    Returns:
        list[CustomerEmail]: 새 고객 이메일 목록
    """
    handler = EmailHandler(target_email=target_email)
    return await handler.check_new_emails()
