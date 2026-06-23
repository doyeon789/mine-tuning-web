# ERD

현재 프로젝트는 Django 기본 `auth.User` 모델을 사용자 테이블로 사용합니다.
직접 정의한 도메인 모델은 `mine_chat` 앱의 채팅 세션/메시지와 `community` 앱의 게시글/댓글입니다.

커뮤니티 게시글 본문은 마크다운 문자열로 저장되며, 로컬 이미지는 별도 DB 테이블이 아니라 `media/` 파일로 저장된 뒤 이미지 URL이 `community_post.content` 안에 마크다운 형식으로 들어갑니다.

## 전체 도메인 ERD

~~~mermaid
erDiagram
    AUTH_USER ||--o{ MINE_CHAT_CHATSESSION : owns
    MINE_CHAT_CHATSESSION ||--o{ MINE_CHAT_CHATMESSAGE : contains

    AUTH_USER ||--o{ COMMUNITY_POST : writes
    AUTH_USER ||--o{ COMMUNITY_COMMENT : writes
    COMMUNITY_POST ||--o{ COMMUNITY_COMMENT : has

    AUTH_USER ||--o{ COMMUNITY_POST_LIKED_USERS : likes
    COMMUNITY_POST ||--o{ COMMUNITY_POST_LIKED_USERS : liked_by

    AUTH_USER {
        bigint id PK
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
        bigint id PK
        bigint owner_id FK "nullable"
        varchar title "max_length=120"
        datetime created_at
        datetime updated_at
    }

    MINE_CHAT_CHATMESSAGE {
        bigint id PK
        bigint session_id FK
        varchar role "user|assistant, max_length=20"
        text content
        datetime created_at
    }

    COMMUNITY_POST {
        bigint id PK
        bigint author_id FK
        varchar title "max_length=120"
        text content "Markdown"
        integer view_count
        datetime created_at
        datetime updated_at
    }

    COMMUNITY_COMMENT {
        bigint id PK
        bigint post_id FK
        bigint author_id FK
        text content "max_length=1000"
        datetime created_at
        datetime updated_at
    }

    COMMUNITY_POST_LIKED_USERS {
        bigint id PK
        bigint post_id FK
        bigint user_id FK
    }
~~~

## 관계

| From | To | Cardinality | FK | Delete rule |
| --- | --- | --- | --- | --- |
| `auth_user` | `mine_chat_chatsession` | 1:N | `mine_chat_chatsession.owner_id` | `CASCADE` |
| `mine_chat_chatsession` | `mine_chat_chatmessage` | 1:N | `mine_chat_chatmessage.session_id` | `CASCADE` |
| `auth_user` | `community_post` | 1:N | `community_post.author_id` | `CASCADE` |
| `community_post` | `community_comment` | 1:N | `community_comment.post_id` | `CASCADE` |
| `auth_user` | `community_comment` | 1:N | `community_comment.author_id` | `CASCADE` |
| `community_post` | `auth_user` | M:N | `community_post_liked_users.post_id`, `community_post_liked_users.user_id` | `CASCADE` |

## 테이블 상세

### `mine_chat_chatsession`

| Column | Type | Null | Key | Description |
| --- | --- | --- | --- | --- |
| `id` | bigint | NO | PK | Django `BigAutoField` |
| `owner_id` | bigint | YES | FK | `auth_user.id` 참조 |
| `title` | varchar(120) | NO | | 채팅방 제목 |
| `created_at` | datetime | NO | | 생성 시간 |
| `updated_at` | datetime | NO | | 수정 시간 |

정렬 기준: `updated_at` 내림차순

### `mine_chat_chatmessage`

| Column | Type | Null | Key | Description |
| --- | --- | --- | --- | --- |
| `id` | bigint | NO | PK | Django `BigAutoField` |
| `session_id` | bigint | NO | FK | `mine_chat_chatsession.id` 참조 |
| `role` | varchar(20) | NO | | `user` 또는 `assistant` |
| `content` | text | NO | | 메시지 본문 |
| `created_at` | datetime | NO | | 생성 시간 |

정렬 기준: `created_at` 오름차순

### `community_post`

| Column | Type | Null | Key | Description |
| --- | --- | --- | --- | --- |
| `id` | bigint | NO | PK | Django `BigAutoField` |
| `author_id` | bigint | NO | FK | `auth_user.id` 참조 |
| `title` | varchar(120) | NO | | 게시글 제목 |
| `content` | text | NO | | 마크다운 본문과 마크다운 이미지 URL |
| `view_count` | integer | NO | | 게시글 조회수, 기본값 `0` |
| `created_at` | datetime | NO | | 작성 시간 |
| `updated_at` | datetime | NO | | 마지막 수정 시간 |

정렬 기준: `created_at` 내림차순, `id` 내림차순

`Post.is_edited`는 `updated_at`이 `created_at`보다 1초 이상 늦은지 판단하는 Python property입니다. DB 컬럼은 아닙니다.

`Post.like_count`는 `liked_users.count()` 값을 반환하는 Python property입니다. DB 컬럼은 아닙니다.

### `community_comment`

| Column | Type | Null | Key | Description |
| --- | --- | --- | --- | --- |
| `id` | bigint | NO | PK | Django `BigAutoField` |
| `post_id` | bigint | NO | FK | `community_post.id` 참조 |
| `author_id` | bigint | NO | FK | `auth_user.id` 참조 |
| `content` | text | NO | | 댓글 본문, 최대 1000자 |
| `created_at` | datetime | NO | | 작성 시간 |
| `updated_at` | datetime | NO | | 마지막 수정 시간 |

정렬 기준: `created_at` 오름차순, `id` 오름차순

### `community_post_liked_users`

`Post.liked_users` 다대다 관계를 위해 Django가 생성하는 중간 테이블입니다.

| Column | Type | Null | Key | Description |
| --- | --- | --- | --- | --- |
| `id` | bigint | NO | PK | Django `BigAutoField` |
| `post_id` | bigint | NO | FK | `community_post.id` 참조 |
| `user_id` | bigint | NO | FK | `auth_user.id` 참조 |

한 사용자가 같은 게시글을 중복으로 좋아요하지 않도록 `post_id`, `user_id` 조합에 unique 제약이 생성됩니다.

## 마크다운 이미지 저장 구조

로컬 이미지는 게시글 테이블의 별도 컬럼이나 이미지 테이블에 저장하지 않습니다.

1. 로그인한 사용자가 글 작성/수정 화면의 내용 영역에 이미지를 드롭하거나 붙여넣습니다.
2. 프론트엔드가 `community:markdown_image_upload` API로 이미지를 업로드합니다.
3. 서버는 PNG, JPEG, GIF, WEBP 형식과 최대 5MB 크기를 검사합니다.
4. 파일은 `MEDIA_ROOT/community/markdown/<user_id>/<uuid>.<ext>` 경로에 저장됩니다.
5. API는 `/media/community/markdown/...` URL을 반환합니다.
6. 편집기는 아래 형식의 마크다운을 `community_post.content`에 삽입합니다.

~~~markdown
![이미지 설명](/media/community/markdown/1/example.png)
~~~

따라서 ERD에는 별도 이미지 엔티티가 없고, 게시글과 이미지 파일의 연결 정보는 `content` 안의 마크다운 URL로 유지됩니다.

## Django 기본/인증 관련 테이블

현재 DB에는 직접 정의한 도메인 테이블 외에도 Django와 `django-allauth`가 사용하는 기본 테이블이 함께 존재합니다.

| App | Tables |
| --- | --- |
| `auth` | `auth_user`, `auth_group`, `auth_permission`, `auth_user_groups`, `auth_user_user_permissions`, `auth_group_permissions` |
| `contenttypes` | `django_content_type` |
| `admin` | `django_admin_log` |
| `sessions` | `django_session` |
| `sites` | `django_site` |
| `allauth` | `account_emailaddress`, `socialaccount_socialaccount`, `socialaccount_socialapp`, `socialaccount_socialtoken` |
| `migrations` | `django_migrations` |
