0323 작업분 기준

정리된 개발일지
[chart 추가 관련](https://mssay2-2.slack.com/docs/T0AHB4Y9LNQ/F0AN0MUM2DR)
[localstorage 기준 누적 state 구현 관련](https://mssay2-2.slack.com/docs/T0AHB4Y9LNQ/F0APHGCA7SL)

# 0323 update
- 사이사이 자질구레한 업데이트분(서술생략)
- stateless 테스트를 위한 임시 front-end 

/chat_test.html

line 412~439 부분을 통해 localstorage에 저장/합니다

폴더에서  python -m http.server 3000 실행 후
http://localhost:3000/chat_test.html 로 접속 가능
~답변 출력 형식은 정돈하지 않았습니다.~ 0325 일부 정리



# stateless 업데이트를 위한 참고용 방안
front-end에서 localstorage에 변수를 저장하는 방식을 기준으로 하며,
변수명은 프로그램이 굴러가는 선에서 자유롭게 변경(필요시연락)해주시면 됩니다.

front(JS)
```ruby
// 저장
localStorage.setItem('financeParams', JSON.stringify(params));

// 불러오기 (페이지 로드 시)
const saved = localStorage.getItem('financeParams');
const [params, setParams] = useState(
  saved ? JSON.parse(saved) : defaultParams
);
```

api_server에서 current_params 추가
```ruby
# api_server 쪽 Request 모델
class QueryRequest(BaseModel):
    question: str
    current_params: dict | None = None  # ← 추가 필요

# @app.post("/api/v1/query") 파트
result = await finance_agent.generate_draft(
    question=request.question,
    current_params=request.current_params,  # ← 추가 필요
    retry_prompt=request.retry_prompt,
    profile=request.profile,)

# api_server 쪽 Response 모델
return {
    "result": draft,
    "updated_params": variables,  # ← generate_draft에서 variables 반환 필요
}
```


# 0311 작업
- 중구난방으로 흩어져있던 트라이 흔적 갈무리
- 어떤 형태든 안되는 방법은 제외 / 우선은 콘솔창에서 입력-출력이 되는가

- (18:10 추가) 누적치 반영을 위해 프롬프트 및 함수 추가
  
/main_agent.py 

/user_functions.py

/skills/investment-simulation.yaml



  개인-콘솔 작업중에는 api키를 하드코딩
  
  업로드 파일엔 일단 OPENAI_API_KEY 로 대체해두었다.
  
  대체하는김에 주석파트를 살짝 정리



- 결과 히스토그램의 경우 현재는 따로 구동중 ( 대화-plugin함수의 함수와 다른 파일에 작업된 상태 )
  
/graph/graph.ipynb




#  ~팀원과의 구동환경-버전에 차이 존재~ **0323 기준) 3.12로 버전 변경.**
~~
0311 기준) python **3.9.13**

그 외의 pip 패키지의 경우 전체 업데이트상태(최신버전)

:  버전 문제의 이슈로 Kernel 관련 수정했던 사항 존재

[해당 개발일지 글](https://mssay2-2.slack.com/archives/C0AHCKN9NSH/p1773133400649859),

[위 글의 추가 참고 이미지](https://mssay2-2.slack.com/archives/C0AHCKN9NSH/p1773133400649859)
~~