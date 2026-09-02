쇼핑레이더 설치 순서
====================

권장 저장소 이름: shopping-radar
예상 주소: https://kimjunnem.github.io/shopping-radar/

1) GitHub에서 새 PUBLIC 저장소 shopping-radar 생성
2) 이 ZIP의 '내용물'을 저장소 루트에 모두 업로드
   - .github 폴더는 숨김 폴더라 Windows 업로드에서 빠질 수 있으니 반드시 확인
3) Settings > Pages
   - Deploy from a branch
   - main / (root)
4) 쿠팡 파트너스 API 사용 권한/키를 발급받은 뒤 Settings > Secrets and variables > Actions에 등록
   - COUPANG_ACCESS_KEY
   - COUPANG_SECRET_KEY
   - COUPANG_SUB_ID (선택: 파트너스에서 등록한 채널 ID가 있으면 사용)
5) Actions > Update shopping radar > Run workflow
6) 실행 성공 후 product/, category/, sitemap.xml이 자동 생성됨

중요
----
- 쿠팡 페이지를 직접 크롤링하지 않습니다.
- 리뷰 원문을 복사하지 않습니다. '상품·후기 보기' 버튼으로 쿠팡 페이지에 연결합니다.
- 메인의 '인기상품 100'은 카테고리별 베스트를 모아 최대 100개로 표시한 것이며,
  쿠팡 전체 판매량 TOP100이라고 표시하지 않습니다.
- API 엔드포인트/카테고리 제공 범위는 쿠팡 파트너스 계정의 최신 문서를 우선합니다.
- API 키는 코드에 직접 넣지 말고 GitHub Secrets에만 보관하세요.

AdSense
-------
현재 파일에는 기존 publisher ID의 AdSense 자동광고 스크립트가 포함되어 있습니다.
실제 광고 노출 여부는 AdSense 승인/사이트 설정에 따릅니다.

매일 오전 8:10(KST)에 자동 갱신되도록 설정되어 있습니다.
