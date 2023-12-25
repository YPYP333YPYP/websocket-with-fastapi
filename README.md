# FastAPI 실시간 채팅 구현

FastAPI를 사용하여 실시간 채팅을 구현한 간단한 프로젝트 입니다.

## 개요

FastAPI와 WebSocket을 활용하여 실시간 채팅 기능을 구현했습니다. Pydantic을 통해 값의 유효성 검사를 진행했으며, sqlalchemy를 통해 ORM 기능을 수행했습니다.
사용한 DB는 Mysql이며 실시간 채팅 방식은 redis의 pub/sub 구조를 이용했습니다.

## 기능

- 회원가입: 사용자는 유저 이름, 비밀번호, 휴대전화 번호를 입력하여 회원가입할 수 있습니다.
- 로그인: 등록된 사용자는 유저 이름과 비밀번호를 입력하여 로그인할 수 있습니다.
- 채팅방 생성: 로그인한 사용자는 여러 채팅방 중 하나를 선택하여 입장할 수 있습니다.
- 실시간 채팅: 채팅방에 참여한 사용자들끼리 실시간으로 메시지를 주고받을 수 있습니다.


| API  | URL                                     | 설명                      |
|------|-----------------------------------------|---------------------------|
| POST | /user/signup                            | 사용자 회원가입            |
| POST | /user/login                             | 로그인                    |
| GET  | /user/{user_id}                         | 사용자 정보 조회          |
| PUT  | /user/update_profile/{user_id}          | 사용자 프로필 업데이트    |
| GET  | /user/deactivate/{user_id}              | 사용자 비활성화           |
| POST | /room/create                            | 채팅방 생성               |
| POST | /room/join                              | 채팅방 참여               |
| PUT  | /room/update/{room_id}                  | 채팅방 정보 업데이트      |
| GET  | /room/rooms                             | 채팅방 목록 조회          |
| GET  | /room/{room_id}/{manager_id}/expel/{user_id} | 채팅방 멤버 추방      |
| GET  | /room/{room_id}/members                 | 채팅방 멤버 목록 조회    |
| GET  | /room/hashtag/{room_id}/add/{hashtag_id} | 채팅방 해시태그 추가     |
| DELETE | /room/hashtag/{room_id}/delete/{hashtag_id} | 채팅방 해시태그 삭제  |
| GET  | /room/category/{room_id}/add/{category_id} | 채팅방 카테고리 추가   |
| DELETE | /room/category/{room_id}/delete        | 채팅방 카테고리 삭제     |
| GET  | /room/search/                           | 카테고리로 채팅방 검색   |
| POST | /hashtag/                               | 해시태그 생성             |
| GET  | /hashtag/all                            | 모든 해시태그 조회        |
| GET  | /hashtag/get/{hashtag_id}               | 특정 해시태그 조회        |
| PUT  | /hashtag/update/{hashtag_id}            | 해시태그 업데이트         |
| DELETE | /hashtag/delete/{hashtag_id}          | 해시태그 삭제             |
| POST | /category/                              | 카테고리 생성             |
| GET  | /category/all                           | 모든 카테고리 조회        |
| GET  | /category/get/{category_id}             | 특정 카테고리 조회        |
| PUT  | /category/update/{category_id}          | 카테고리 업데이트         |
| DELETE | /category/delete/{category_id}        | 카테고리 삭제             |

## 예시 화면
![화면](https://github.com/YPYP333YPYP/websocket-with-fastapi/assets/57821687/13e68b94-e668-472e-9a1c-642f6e509444)

