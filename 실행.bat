@echo off
chcp 65001 > nul
echo.
echo  =========================================
echo   나의 대시보드 시작 중...
echo  =========================================
echo.

REM 필요한 패키지 설치 (최초 1회)
py -m pip install streamlit anthropic python-dotenv --quiet --disable-pip-version-check

echo.
echo  브라우저가 자동으로 열립니다.
echo  종료하려면 이 창을 닫으세요.
echo.

REM 앱 실행
py -m streamlit run "%~dp0app.py" --server.headless false

pause
