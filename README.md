## Location based app

Identify nearby users and explore shared interests.

Exact locations and interests remain confidential from the server (noise added before sending to server for privacy).

Using: **FastAPI**, **PostgreSQL**, PostGIS extension (adds support
for geographic objects)

### Features

- Send location update (authentication required. All sample users are initialized with password=“secret”).
- Find nearby users (authentication required)
- Visualize true location vs. the noisy location of current user.
- 3-step process of finding private set intersection of interests between two nearby users (simple implementation)