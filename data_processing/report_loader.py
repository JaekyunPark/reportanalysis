"""
보고서 로더
"""
import PyPDF2
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class ReportLoader:
    """보고서 문서 로더"""
    
    @staticmethod
    def load_pdf(file_path: str) -> str:
        """
        PDF 파일에서 텍스트 추출
        
        Args:
            file_path: PDF 파일 경로
            
        Returns:
            추출된 텍스트
        """
        try:
            logger.info(f"PDF 로드 중: {file_path}")
            
            text_content = []
            
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                total_pages = len(pdf_reader.pages)
                
                logger.info(f"총 {total_pages}페이지 처리 중...")
                
                for page_num, page in enumerate(pdf_reader.pages, 1):
                    text = page.extract_text()
                    if text.strip():
                        # 페이지 마커 삽입
                        page_text = f"[PAGE {page_num}] {text}"
                        text_content.append(page_text)
                    
                    if page_num % 10 == 0:
                        logger.info(f"{page_num}/{total_pages} 페이지 처리 완료")
            
            full_text = "\n\n".join(text_content)
            logger.info(f"PDF 로드 완료: {len(full_text)} 문자")
            
            # 페이지 마커가 보존되도록 전처리 전 호출
            return ReportLoader._preprocess_text(full_text)
            
        except Exception as e:
            logger.error(f"PDF 로드 실패: {str(e)}")
            raise
    
    @staticmethod
    def load_text(file_path: str, encoding: str = 'utf-8') -> str:
        """
        텍스트 파일 로드
        
        Args:
            file_path: 텍스트 파일 경로
            encoding: 파일 인코딩
            
        Returns:
            파일 내용
        """
        try:
            logger.info(f"텍스트 파일 로드 중: {file_path}")
            
            with open(file_path, 'r', encoding=encoding) as file:
                content = file.read()
            
            logger.info(f"텍스트 파일 로드 완료: {len(content)} 문자")
            
            return ReportLoader._preprocess_text(content)
            
        except UnicodeDecodeError:
            # UTF-8 실패 시 다른 인코딩 시도
            logger.warning(f"UTF-8 디코딩 실패, cp949 시도 중...")
            try:
                with open(file_path, 'r', encoding='cp949') as file:
                    content = file.read()
                logger.info(f"cp949로 로드 완료: {len(content)} 문자")
                return ReportLoader._preprocess_text(content)
            except Exception as e:
                logger.error(f"텍스트 파일 로드 실패: {str(e)}")
                raise
        except Exception as e:
            logger.error(f"텍스트 파일 로드 실패: {str(e)}")
            raise
    
    @staticmethod
    def _preprocess_text(text: str) -> str:
        """
        텍스트 전처리
        
        Args:
            text: 원본 텍스트
            
        Returns:
            전처리된 텍스트
        """
        # 연속된 공백 제거
        import re
        text = re.sub(r'\s+', ' ', text)
        
        # 연속된 줄바꿈 정리 (최대 2개까지만)
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        return text.strip()
