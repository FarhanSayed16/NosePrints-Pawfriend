# Staff UX + nationwide ops pass

## Verified / implemented

- Login busy state; queue error surfacing; Refresh; Show reviewed
- `top_match_dog_id` used for selection clear after delete
- Confirm/reject double-submit guard; viewer cannot decide
- Strict empty-state copy (likely-only messaging)
- Admin: invite, team roles, deactivate, audit list
- Forgot password + accept-invite routes
- Registry table + region filter; DPDP erasure tab (admin)
- Visual ops console redesign (`Staff.css`)

## Manual checklist

1. Login success / bad password fails cleanly
2. Queue loads + Refresh; Show reviewed
3. Confirm shows owner; Reject clears pending
4. Non-admin cannot delete / open Admin
5. Invite returns email or copyable staging URL
6. Reset password flow completes and logs in
7. Erase owner removes dogs (admin)
