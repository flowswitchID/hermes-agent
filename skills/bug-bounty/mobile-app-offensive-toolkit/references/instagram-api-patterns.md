# Instagram API Patterns (from binary analysis)

## GraphQL Endpoints

- Followers: `https://www.instagram.com/graphql/query/?query_hash=c76146de99bb02f6415203be841dd25a&id={user_id}&first=100&after={cursor}`
- Following: `https://www.instagram.com/graphql/query/?query_hash=d04b0a864b4b54837c0d870b0e77e076&id={user_id}&first=100&after={cursor}`

Response structure:
```json
{
  "data": {
    "user": {
      "edge_followed_by": {
        "edges": [{"node": {"username": "..."}}],
        "page_info": {"has_next_page": true, "end_cursor": "..."}
      }
    }
  }
}
```

## Mobile API v1

- Login: `POST https://i.instagram.com/api/v1/accounts/login/`
- Following list: `GET https://i.instagram.com/api/v1/friendships/{user_id}/following/?count=12&max_id={max_id}`
- Web profile info: `GET https://i.instagram.com/api/v1/users/web_profile_info/?username={username}`

Mobile following response:
```json
{
  "users": [{"username": "..."}],
  "next_max_id": "..."
}
```

## Web Endpoints

- Login AJAX: `POST https://www.instagram.com/accounts/login/ajax/`
- Login page (CSRF): `GET https://www.instagram.com/accounts/login/`
- Profile info: `GET https://i.instagram.com/api/v1/users/web_profile_info/?username={username}`

## App IDs

- Web: `936619743392459`
- Mobile: `567067343352427`

## Headers

### Web
- `User-Agent`: iPhone or desktop UA
- `X-IG-App-ID`: `936619743392459`
- `X-CSRFToken`: from cookies
- `X-Requested-With`: `XMLHttpRequest`
- `Origin`: `https://www.instagram.com`
- `Referer`: `https://www.instagram.com/`

### Mobile
- `User-Agent`: Instagram Android UA (e.g., `Instagram 202.0.0.34.68 Android (33/13; ...)`)
- `X-IG-App-Id`: `567067343352427`
- `X-IG-Device-Id`: random `android-` + md5
- `X-IG-Family-Device-Id`: random UUID
- `X-IG-Android-Id`: `android-` + md5 of (username+password)
- `X-IG-Capabilities`: `3brTv10=`
- `X-IG-Connection-Type`: `WIFI` or `MOBILE(LTE)`
- `X-Pigeon-Session-Id`: `UFS-<uuid>-0`
- `X-Bloks-Version-Id`: platform-specific (from reference: `15bf7599a6f3cb0873174fecc7a0d90acdb96492075190bb2a6bab442cc3edc8` or `9fc6a7a4a577456e492c189810755fe22a6300efc23e4532268bca150fe3e27a`)
- `X-Mid`: 28-char alphanumeric random
- `X-Fb-Connection-Type`: `MOBILE.LTE`
- `X-Fb-Http-Engine`: `Tigon-HUC-Fallback` or `Liger`
- `Priority`: `u=3`

## Query Hashes

- Followers: `c76146de99bb02f6415203be841dd25a`
- Following: `d04b0a864b4b54837c0d870b0e77e076`
- Alternative followers (from original binary): `58712303d941c6855d4e888c5f0cd22f`
- Alternative hashtag: `9b498c08113f1e09617a1703c22b2f32`

## Encryption

- Password XOR key: 100-byte hex sequence (0x00 through 0x63)
- Format: `ig_set_password_encryption_key_id#<base64(xor(password, key))>`
- Mobile plaintext: `#PWD_INSTAGRAM:0:{timestamp}:{password}`
- Web plaintext: `#PWD_INSTAGRAM_BROWSER:0:{ncek}:{password}`

## Cookie validation

- `GET https://i.instagram.com/api/v1/users/web_profile_info/?username=self`
- Headers: `user-agent`, `x-ig-app-id`, `cookie`
- Success: 200 with `data.user.username`

## Success detection in login response

- Body contains `logged_in_user` (mobile API)
- Body contains `userId` (web AJAX)
- Body contains `Bearer IGT:2:` (session token)
- JSON field `authenticated: true`
- HTTP 200 + redirect
