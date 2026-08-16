# Presentation Coaching Program

발표 음성을 분석하여 발화 비유창성 후보 구간을 탐지하고, 사용자가 해당 구간의 의미 구조를 다시 정리한 뒤 재발화하도록 돕는 웹 기반 발표 코칭 프로그램입니다.

## 1. 프로그램 구조

발표 음성을 입력하면 다음 네 단계를 거쳐 분석합니다.

### A. 음성 신호 분석
- Librosa를 이용한 speech / non-speech 분석
- pause 탐지
- F0, spectral flatness, RMS 계산

### B. 음성 텍스트 변환
- OpenAI Whisper 모델을 로컬에서 실행
- 한국어 전사
- 단어별 timestamp 추출

### C. 언어 구조 분석
- 문장 분리
- 연결어·연결 어미 기반 의미 단위 근사 분할
- 반복 및 재시작 후보 탐지

### D. 통합 판단
- pause, filler, repetition/restart 정보를 시간축으로 통합
- 비유창성 코칭 후보 구간 제시

## 2. 실행 환경

- Python 3.x
- FFmpeg
- Streamlit
- Librosa
- OpenAI Whisper
- NumPy
- SoundFile

Whisper 모델: `small`

현재 프로그램은 OpenAI API를 사용하지 않으며, Whisper 모델을 로컬 환경에서 실행합니다.

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

웹 프로그램을 실행합니다.

```bash
streamlit run app.py
```

실행 후 브라우저에 표시되는 로컬 주소로 접속합니다.

## 5. 사용 방법

1. 발표 음성을 직접 녹음하거나 WAV 파일을 업로드합니다.
2. 1차 발표를 분석합니다.
3. 비유창성 코칭 후보 구간과 판단 근거를 확인합니다.
4. 해당 구간에서 전달하려던 핵심 개념과 내용 간 관계를 다시 정리합니다.
5. 같은 내용을 자신의 언어로 다시 발표합니다.
6. 2차 발표를 분석하여 코칭 전후 결과를 비교합니다.

## 6. 주요 파일

```text
app.py                 웹 인터페이스
audio_analysis.py      음성 신호 분석
transcription.py       Whisper 기반 음성 전사
language_analysis.py   언어 구조 분석
scoring.py             통합 판단 및 점수화
config.py              분석 설정값
requirements.txt       Python 의존성
packages.txt           시스템 의존성
```

## 7. 이식성

`.venv`와 다운로드된 Whisper 모델 자체를 저장하지 않습니다.

새로운 컴퓨터에서는 저장소를 clone한 뒤 가상환경과 실행 환경을 다시 생성합니다.

즉, 실행 환경 자체를 옮기는 것이 아니라 실행 환경을 재구성할 수 있는 명세를 저장하는 것을 원칙으로 합니다.
