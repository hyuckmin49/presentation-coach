# Presentation Coaching Program

발표 음성을 분석하여 발화 비유창성 후보 구간을 탐지하고, 사용자가 해당 구간과 발표 전체의 의미 구조를 다시 정리한 뒤 총 3차례 재발화하도록 돕는 웹 기반 발표 코칭 프로그램입니다.

**웹앱:** https://presentation-coach-3uzcdbybtceyigx72p9qup.streamlit.app/

이 프로그램은 발표 내용을 평가하거나 정답 문장을 제시하지 않습니다. 발표를 외우는 대신 핵심 개념과 내용의 관계를 머릿속에 구조화하고, 같은 내용을 자신의 언어로 다시 말하는 과정을 지원합니다.

## 1. 프로그램 구조

발표 음성을 입력하면 다음 네 단계를 거쳐 분석합니다.

### A. 음성 신호 분석
- Librosa를 이용한 speech / non-speech 분석
- pause 탐지
- F0, spectral flatness, RMS 계산
- 길고 평탄한 유성음에 기반한 음 끌기 후보 탐지

### B. 음성 텍스트 변환
- OpenAI Whisper 모델을 로컬에서 실행
- 한국어 전사
- 단어별 timestamp 추출

### C. 언어 구조 분석
- 문장 분리
- 연결어·연결 어미 기반 의미 단위 근사 분할
- 반복 및 재시작 후보 탐지
- 한 문장 안에서 두 번째 이후의 `약간` 반복 탐지

### D. 통합 판단
- pause, filler, repetition/restart, 음 끌기 정보를 시간축으로 통합
- 비유창성 코칭 후보 구간 제시

분석 결과는 잘못된 발화에 대한 확정 판정이 아니라 사용자가 직접 확인할 **보완 후보**입니다.

## 2. 실행 환경

- Python 3.x
- FFmpeg
- Streamlit
- Librosa
- OpenAI Whisper
- NumPy
- SoundFile

Whisper 모델: `small`

현재 프로그램은 OpenAI API를 사용하지 않으며, Whisper 모델을 프로그램 실행 환경에서 직접 구동합니다. 전사는 한국어로 고정하되 발표에 포함된 일부 영어 단어도 Whisper가 함께 전사하도록 구성되어 있습니다.

## 3. 설치

저장소를 복제합니다.

```bash
git clone https://github.com/hyuckmin49/presentation-coach.git
cd presentation-coach
```

가상환경을 생성합니다.

### Windows

```bash
python -m venv .venv
.venv\Scripts\activate
```

필요한 Python 패키지를 설치합니다.

```bash
pip install -r requirements.txt
```

FFmpeg가 설치되어 있어야 합니다.

## 4. 실행

배포된 웹앱은 다음 주소에서 바로 사용할 수 있습니다.

https://presentation-coach-3uzcdbybtceyigx72p9qup.streamlit.app/

로컬 환경에서 실행하려면 다음 명령을 사용합니다.

```bash
streamlit run app.py
```

실행 후 브라우저에 표시되는 로컬 주소로 접속합니다.

## 5. 사용 방법

1. 프로그램 소개와 사용 방법을 확인한 뒤 `시작해 보기`를 누릅니다.
2. 최종 PDF에 표시할 학번과 이름을 입력합니다.
3. 1차 발표를 웹에서 녹음하거나 WAV 파일로 업로드합니다.
4. 음성 길이를 바탕으로 표시되는 예상시간과 A~D 분석 진행 상황을 확인합니다.
5. 발표 전문에서 노란색으로 표시된 보완 후보와 탐지 근거를 확인합니다.
6. 각 보완 후보의 핵심 개념과 내용 간 관계를 **부분 구조 메모**에 작성합니다.
7. 부분을 점검한 뒤 발표 전체의 흐름을 **전체 구조 메모**에 작성합니다.
8. 같은 내용을 자신의 언어로 다시 발표하며 위 과정을 2차와 3차까지 반복합니다.
9. 최종 비교 화면에서 세 회차의 결과를 확인하고 피드백 PDF를 내려받습니다.

부분 구조 메모와 전체 구조 메모는 필수입니다. 자동 탐지 결과가 없더라도 발표 전문을 직접 읽고 전체 구조를 점검해야 다음 회차로 넘어갈 수 있습니다.

## 6. 최종 피드백 PDF

사용자에게 제공되는 결과 파일은 PDF 한 개입니다. PDF에는 다음 내용이 포함됩니다.

- 학번과 이름
- 1~3차 발표 전문
- 전문에 표시된 보완 후보 하이라이트
- 보완 후보 구간과 판단 근거
- 사용자가 작성한 부분 구조 메모
- 회차별 전체 구조 메모

학번·이름, 음성, 전사 결과와 메모는 현재 브라우저 세션에서만 사용됩니다. 별도의 사용자 기록 파일은 저장하지 않으며, 세션이 종료되면 다시 불러올 수 없습니다.

## 7. 주요 파일

```text
app.py                 웹 인터페이스
analysis_time.py       음성 길이 기반 예상 분석시간 계산
audio_analysis.py      음성 신호 분석
transcription.py       Whisper 기반 음성 전사
language_analysis.py   언어 구조 분석
scoring.py             통합 판단 및 점수화
feedback_report.py     최종 PDF 생성
transcript_highlight.py 발표 전문 하이라이트 처리
config.py              분석 설정값
requirements.txt       Python 의존성
packages.txt           시스템 의존성
```

## 8. 테스트

```bash
python -m unittest discover -s tests -v
```

예상 분석시간, 음 끌기 탐지, `약간` 반복, 통합 점수화, 전문 하이라이트, PDF 생성과 Whisper 설정을 자동 테스트합니다.

## 9. 이식성

`.venv`와 다운로드된 Whisper 모델 자체를 저장하지 않습니다.

새로운 컴퓨터에서는 저장소를 clone한 뒤 가상환경과 실행 환경을 다시 생성합니다.

즉, 실행 환경 자체를 옮기는 것이 아니라 실행 환경을 재구성할 수 있는 명세를 저장하는 것을 원칙으로 합니다.
