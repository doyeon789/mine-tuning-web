# ERD

현재 프로젝트는 Django 기본 `auth.User` 모델을 사용합니다. 커스텀 도메인 모델은 `mine_chat` 앱의 채팅 세션/메시지와 `community` 앱의 게시글까지 총 3개입니다.

## 핵심 도메인 ERD

~~~mermaid
erDiagram
    AUTH_USER ||--o{ MINE_CHAT_CHATSESSION : owns
    MINE_CHAT_CHATSESSION ||--o{ MINE_CHAT_CHATMESSAGE : contains
    AUTH_USER ||--o{ COMMUNITY_POST : writes

    AUTH_USER {
        int id PK
        varchar username UK
        varchar password
        varchar email
        varchar first_name
        varchar last_name
        bool is_superuser
        bool is_staff
        bool is_active
        datetime last_login
        datetime date_joined
    }

    MINE_CHAT_CHATSESSION {
        int id PK
        int owner_id FK "nullable"
        varchar title "max_length=120"
        datetime created_at
        datetime updated_at
    }

    MINE_CHAT_CHATMESSAGE {
        int id PK
        int session_id FK
        varchar role "user|assistant, max_length=20"
        text content
        datetime created_at
    }

    COMMUNITY_POST {
        int id PK
        int author_id FK
        varchar title "max_length=120"
        text content "Markdown"
        datetime created_at
        datetime updated_at
    }
~~~

## 관계

| From | To | Cardinality | FK | Delete rule |
| --- | --- | --- | --- | --- |
| `auth_user` | `mine_chat_chatsession` | 1:N | `mine_chat_chatsession.owner_id` | `CASCADE` |
| `mine_chat_chatsession` | `mine_chat_chatmessage` | 1:N | `mine_chat_chatmessage.session_id` | `CASCADE` |
| `auth_user` | `community_post` | 1:N | `community_post.author_id` | `CASCADE` |

## 테이블 상세

### `mine_chat_chatsession`

| Column | Type | Null | Key | Description |
| --- | --- | --- | --- | --- |
| `id` | integer | NO | PK | Django `BigAutoField` |
| `owner_id` | integer | YES | FK | `auth_user.id` 참조 |
| `title` | varchar(120) | NO | | 채팅방 제목 |
| `created_at` | datetime | NO | | 생성 시간 |
| `updated_at` | datetime | NO | | 수정 시간 |

인덱스:

| Name | Columns |
| --- | --- |
| `mine_chat_chatsession_owner_id_56a86a40` | `owner_id` |

### `mine_chat_chatmessage`

| Column | Type | Null | Key | Description |
| --- | --- | --- | --- | --- |
| `id` | integer | NO | PK | Django `BigAutoField` |
| `session_id` | integer | NO | FK | `mine_chat_chatsession.id` 참조 |
| `role` | varchar(20) | NO | | `user` 또는 `assistant` |
| `content` | text | NO | | 메시지 본문 |
| `created_at` | datetime | NO | | 생성 시간 |

인덱스:

| Name | Columns |
| --- | --- |
| `mine_chat_chatmessage_session_id_fa8d89eb` | `session_id` |

### `community_post`

| Column | Type | Null | Key | Description |
| --- | --- | --- | --- | --- |
| `id` | integer | NO | PK | Django `BigAutoField` |
| `author_id` | integer | NO | FK | `auth_user.id` 참조 |
| `title` | varchar(120) | NO | | 게시글 제목 |
| `content` | text | NO | | 마크다운 원문 및 마크다운 이미지 URL |
| `created_at` | datetime | NO | | 작성 시간 |
| `updated_at` | datetime | NO | | 마지막 저장 시간 |

인덱스:

| Name | Columns |
| --- | --- |
| `community_post_author_id_a6c5f564` | `author_id` |

`Post.is_edited`는 `updated_at`이 `created_at`보다 1초 이상 늦은지 판별하는 Python 속성으로, DB 컬럼이 아닙니다.

## 마크다운 이미지 저장 구조

로컬 이미지는 게시글 테이블의 별도 컬럼이나 이미지 테이블에 저장하지 않습니다.

1. 로그인 사용자가 이미지 업로드 API를 호출합니다.
2. 파일은 `MEDIA_ROOT/community/markdown/&lt;user_id&gt;/&lt;uuid&gt;.&lt;확장자&gt;`에 저장됩니다.
3. API가 `/media/community/markdown/...` URL을 반환합니다.
4. 편집기가 다음 형태의 마크다운을 `community_post.content`에 삽입합니다.

~~~markdown
![이미지 설명](/media/community/markdown/1/example.png)
~~~

따라서 ERD에는 별도의 이미지 엔터티가 없으며, 파일과 게시글의 연결 정보는 `content` 내부의 마크다운 URL로 유지됩니다.

## Django 기본 테이블

현재 SQLite DB에는 Django 기본 앱과 `django-allauth` 관련 테이블도 함께 존재합니다.

~~~mermaid
erDiagram
    DJANGO_CONTENT_TYPE ||--o{ AUTH_PERMISSION : has
    AUTH_GROUP ||--o{ AUTH_GROUP_PERMISSIONS : has
    AUTH_PERMISSION ||--o{ AUTH_GROUP_PERMISSIONS : included_in
    AUTH_USER ||--o{ AUTH_USER_GROUPS : has
    AUTH_GROUP ||--o{ AUTH_USER_GROUPS : includes
    AUTH_USER ||--o{ AUTH_USER_USER_PERMISSIONS : has
    AUTH_PERMISSION ||--o{ AUTH_USER_USER_PERMISSIONS : granted
    AUTH_USER ||--o{ DJANGO_ADMIN_LOG : writes
    DJANGO_CONTENT_TYPE ||--o{ DJANGO_ADMIN_LOG : describes
~~~

대상 테이블:

| App | Tables |
| --- | --- |
| `auth` | `auth_user`, `auth_group`, `auth_permission`, `auth_user_groups`, `auth_user_user_permissions`, `auth_group_permissions` |
| `contenttypes` | `django_content_type` |
| `admin` | `django_admin_log` |
| `sessions` | `django_session` |
| `sites` | `django_site` |
| `allauth` | `account_emailaddress`, `socialaccount_socialaccount`, `socialaccount_socialapp`, `socialaccount_socialtoken` |
| `migrations` | `django_migrations` |
