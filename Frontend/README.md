# Home Cloud: LAN-based file storage with a web front end

## **Main Functions：**

1. **Quick scraping and navigation on the main page**
    The homepage should include a “media overview” panel that automatically scans and indexes newly added content. It should display quick-access cards for “recently added,” “continue watching,” or “by genre/year/tag.” Users should be able to refresh metadata (titles, posters, actors, duration, resolution) with one click. Navigation should feel seamless, with a persistent top bar (Library, File Manager, Transfer Queue, User Center, Settings) and breadcrumb navigation to move between folders and subdirectories efficiently.
2. **File upload, download, and storage operations**
    Provide multiple ways to move data: (1) direct browser uploads with drag-and-drop, chunked uploading, resume support, and batch folder upload; (2) network mounting (WebDAV, SMB, or NFS) with clear connection URLs; and (3) CLI/desktop client examples (e.g., rclone, curl). Downloads should allow direct links, batch zips, rate limits, and expiring share links with optional passwords. File integrity checks (MD5/SHA256) and storage policies (single disk, RAID, or object storage backends) should be included. Deleted files move to a recycle bin, and versioning enables rolling back to earlier file states.
3. **User login interface**
    The login page should support username/email + password, optional single sign-on (OIDC/SAML), and multi-factor authentication (TOTP, SMS, hardware keys). Enforce password strength checks, attempt throttling, and optional CAPTCHA. Session management should include “remember me” cookies (HttpOnly, SameSite strict), expiration policies, and remote logout for compromised sessions. Registration may be open, invite-only, or admin-approved. First-time login should trigger a setup wizard for personal folders and preferences.
4. **Image and movie file preview**
    Images should display thumbnails instantly, with EXIF data available, and options for full-resolution or screen-fitted view. Slideshow mode supports batch viewing. Video previews should support both direct playback and server-side transcoding (adaptive bitrate streaming via HLS/DASH). Features include subtitle loading (.srt/.ass), multiple audio tracks, playback speed control, progress memory, and auto-play for series. Video thumbnails should show a timeline preview, and users can capture stills or generate contact sheets. Mobile playback should include gesture controls for seeking, brightness, and volume.

## **Extended Function(If possible)**:

1. **External Connection Issues (Virtual LAN, FRP)**
   Many Internet Service Providers do not assign a true **public IP address** to residential or small-business users, instead placing them behind **Carrier-Grade NAT (CGNAT)**. This prevents direct inbound connections from outside the local network, making it difficult to expose services like a home cloud.

   To address this, the system should provide built-in options for external connectivity:

   - **Virtual LAN (VLAN / VPN tunneling):**
     Allow the user to join devices across different networks into a single virtual local network. This can be implemented through Tailscale, ZeroTier, or WireGuard-based tunnels. Users see all devices as if they were on the same LAN, with private IPs assigned to each node, enabling seamless file access and media streaming.
   - **FRP (Fast Reverse Proxy):**
     Provide support for FRP as a lightweight, self-hosted NAT traversal tool. By deploying an FRP server on a VPS or cloud instance with a public IP, the home server can create a persistent outbound tunnel. This tunnel forwards incoming traffic (e.g., HTTP/HTTPS, SMB, SSH) back into the private network. The system should include a configuration UI for FRP, including protocol selection, port mapping, encryption, and optional authentication.