# 과카밀리! PS Vita 일본어판 한글패치 v0.3.0 시험판

PS Vita 일본어판 **PCSG00369**의 게임 텍스트와 타이틀 이미지를 한국어로 바꾼 비공식 rePatch 패치입니다. PC판 *Guacamelee! Super Turbo Championship Edition*의 한국어 패치를 바탕으로 Vita판 문장과 버튼 표기를 조정했습니다. 두 판본이 달라 전체 플레이 검증은 아직 필요합니다.

## 적용 내용

- 메뉴, 대사, 설명 등 일본어 언어표에 한국어 적용
- PC 패치에 없던 Vita 전용 문장 추가
- Vita에서 표시되지 않던 PC 전용 버튼 토큰 36개 수정
- 시작 화면과 메인 메뉴의 일본어 로고를 한국어 이미지로 교체
- 한국어 글꼴 포함

## 다운로드

[v0.3.0 시험판 릴리스](https://github.com/YourFaceMonster/guacamelee-psv-korean-patch/releases/tag/v0.3.0)의 `Guacamelee_PCSG00369_Korean_rePatch_v3.zip` 파일을 받으세요.

## 설치

대상은 일본어판 **PCSG00369**입니다. PS Vita 실기기에는 게임과 rePatch 플러그인이 필요합니다.

1. 게임을 완전히 종료합니다.
2. 기존 `ux0:rePatch/PCSG00369` 폴더가 있다면 백업합니다.
3. ZIP을 풀고 안의 `rePatch` 폴더를 PS Vita의 `ux0:` 최상위에 복사합니다.
4. `ux0:rePatch/PCSG00369/misc.dat`와 `ux0:rePatch/PCSG00369/resources.dat`가 있는지 확인합니다.
5. 게임을 실행합니다.

Vita3K에서는 `ux0/app/PCSG00369/`의 같은 이름 파일을 백업한 뒤 직접 교체해 시험했습니다.

## 확인 상태

- Vita3K 메인 메뉴의 한글 글꼴과 문장 표시는 사용자가 화면으로 확인했습니다.
- v0.3.0에 추가한 버튼 표기 및 타이틀 이미지 수정본은 파일 구조와 해시를 검증했으며, 실제 게임 화면 확인은 진행 중입니다.
- PS Vita 실기기에서 rePatch 적용과 전체 게임 진행은 아직 확인하지 않았습니다.

문제가 있으면 해당 화면, 발생 시점, 게임 버전과 패치 적용 방식을 함께 제보해 주세요.

## 복구

게임을 종료하고 `ux0:rePatch/PCSG00369` 폴더를 다른 곳으로 옮긴 뒤 게임을 다시 실행하세요. 기존 rePatch 폴더를 백업했다면 복원합니다.

## 제작 및 출처

- **YourFaceMonster** — 프로젝트 진행과 테스트
- **버섯순이** — PC판 한국어 번역
- **Snowyegret** — PC판 한국어 패치 기술 작업
- **Codex (OpenAI)** — Vita판 데이터 분석, 번역 조정, 이미지 및 패키지 제작 지원
- **Drinkbox Studios** — 원작 게임 개발
- [PC판 한국어 패치](https://github.com/mushsooni/GuacameleeSTCE_kor/releases)
- [rePatch reDux0](https://github.com/dots-tb/rePatch-reDux0)

게임 및 번역 자료에 임의의 오픈소스 라이선스를 부여하지 않습니다.

