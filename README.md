<div align="center">

# 🎌 BeatAniVerse Bot
### Complete All-in-One Telegram Bot Solution

<p align="center">
  <strong>Link Provider · Group Management · Poster Generation</strong>
</p>

<p align="center">
  <a href="https://t.me/BeatAnime"><img src="https://img.shields.io/badge/Telegram-Channel-blue?style=for-the-badge&logo=telegram" alt="Telegram Channel"></a>
  <a href="https://t.me/Beat_Anime_Discussion"><img src="https://img.shields.io/badge/Telegram-Discussion-blue?style=for-the-badge&logo=telegram" alt="Discussion Group"></a>
  <a href="https://render.com"><img src="https://img.shields.io/badge/Deploy-Render-46E3B7?style=for-the-badge&logo=render" alt="Deploy on Render"></a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/PostgreSQL-NeonDB-4169E1?style=flat-square&logo=postgresql&logoColor=white" alt="PostgreSQL">
  <img src="https://img.shields.io/badge/MongoDB-Atlas-47A248?style=flat-square&logo=mongodb&logoColor=white" alt="MongoDB">
  <img src="https://img.shields.io/badge/License-Proprietary-red?style=flat-square" alt="License">
</p>

---

### 📖 Overview

**BeatAniVerse Bot** is a comprehensive, production-ready Telegram bot that combines three powerful systems into one unified platform. Built for anime communities, this bot provides advanced link management, professional poster generation, and complete group administration capabilities.

</div>

---

## 🌟 Key Features at a Glance

<table>
<tr>
<td width="33%" valign="top">

### 🔗 Link Provider
- Force subscription management
- Expiring & permanent links
- Clone bot system
- Broadcast automation
- Auto-forwarding
- Upload management
- Manga tracking

</td>
<td width="33%" valign="top">

### 🎨 Poster Engine
- 12 professional templates
- 6-layer composition
- AniList/MAL integration
- Premium tier system
- Watermark support
- Custom branding
- High-quality output

</td>
<td width="33%" valign="top">

### 🤖 Group Management
- 77 modular features
- Admin automation
- Anti-spam/flood
- Custom filters
- Welcome system
- Warning system
- Comprehensive logging

</td>
</tr>
</table>

---

## 📦 Project Architecture

```
BeatAniVerse-v2/
│
├── 🤖 Core Bot Files
│   ├── bot.py                        ← Main bot (7986 lines, unified logic)
│   ├── database_dual.py              ← Dual DB layer (NeonDB + MongoDB)
│   ├── database_safe.py              ← Legacy NeonDB-only layer (reference)
│   ├── poster_engine.py              ← 6-layer poster generation engine
│   ├── beataniversebot_compat.py     ← BeatVerse compatibility shim
│   └── health_check.py               ← HTTP health endpoint for monitoring
│
├── 🎨 Assets
│   ├── fonts/                        ← Premium fonts (Poppins, Bebas Neue, etc.)
│   └── iconspng/                     ← Platform logos (Netflix, Crunchyroll, AniList)
│
├── 🔧 Configuration
│   ├── requirements.txt              ← Python dependencies
│   ├── Dockerfile                    ← Container configuration
│   ├── render.yml                    ← Render deployment config
│   └── .env.example                  ← Environment template
│
└── 📚 Modules (77 Features)
    ├── 👑 Administration
    │   ├── admin.py                  ← Group admin: title, description, stickers
    │   ├── promote/demote            ← User privilege management
    │   └── connection.py             ← Multi-group PM management
    │
    ├── 🛡️ Security & Moderation
    │   ├── antiflood.py              ← Anti-flood with configurable actions
    │   ├── bans.py                   ← Ban/unban/kick/temp-ban system
    │   ├── muting.py                 ← Mute/unmute/temp-mute controls
    │   ├── warns.py                  ← Warning system with auto-actions
    │   ├── blacklist.py              ← Message blacklist filter
    │   ├── blacklist_stickers.py     ← Sticker blacklist filter
    │   ├── blacklistusers.py         ← User blacklist system
    │   ├── global_bans.py            ← Cross-group ban system
    │   ├── locks.py                  ← Media/sticker/poll/bot locks
    │   ├── approve.py                ← User approval system
    │   └── nightmode.py              ← Scheduled chat locking
    │
    ├── 🎯 Content Management
    │   ├── notes.py                  ← Saved notes with hashtag shortcuts
    │   ├── cust_filters.py           ← Custom keyword→response filters
    │   ├── welcome.py                ← Custom welcome/goodbye messages
    │   ├── rules.py                  ← Group rules management
    │   ├── purge.py                  ← Message purging tools
    │   ├── cleaner.py                ← Auto-delete service messages
    │   ├── reactions.py              ← Reaction message system
    │   └── log_channel.py            ← Event logging to channel
    │
    ├── 🎭 Anime & Entertainment
    │   ├── anime.py                  ← Anime info (Jikan + AniList)
    │   ├── animequotes.py            ← Random anime quotes
    │   ├── animerequest.py           ← Request system (anti-spam, cooldown)
    │   ├── imdb.py                   ← IMDB movie/show lookup
    │   ├── couples.py                ← Daily couple picker (MongoDB)
    │   ├── fun.py                    ← Fun commands (flip, roll, etc.)
    │   ├── truth_and_dare.py         ← Truth or dare game
    │   └── wallpaper.py              ← Wallpaper search
    │
    ├── 🔧 Utilities
    │   ├── afk.py                    ← AFK status with auto-unmention
    │   ├── userinfo.py               ← User information lookup
    │   ├── users.py                  ← User tracking system
    │   ├── translator.py             ← Multi-language translation
    │   ├── currency_converter.py     ← Live currency conversion
    │   ├── google.py                 ← Google search integration
    │   ├── wiki.py                   ← Wikipedia search
    │   ├── ud.py                     ← Urban Dictionary lookup
    │   ├── telegraph.py              ← Telegraph post creator
    │   ├── fonts.py                  ← Font stylizer
    │   ├── writetool.py              ← Text styling tools
    │   ├── stickers.py               ← Sticker pack management
    │   ├── memify.py                 ← Meme generator
    │   ├── logo.py                   ← Logo generator
    │   ├── sed.py                    ← Text find & replace
    │   ├── zip.py                    ← File zip/unzip
    │   └── reporting.py              ← User reporting system
    │
    ├── 🎮 Engagement
    │   ├── tagall.py                 ← Tag all members
    │   ├── chatbot.py                ← AI chatbot (MongoDB-backed)
    │   ├── inline.py                 ← Inline query mode
    │   └── misc.py                   ← Miscellaneous commands
    │
    ├── 🔐 Privilege Management
    │   ├── disasters.py              ← Global disaster/sudo management
    │   ├── sudoers.py                ← Sudo user management
    │   ├── disable.py                ← Command disable/enable per chat
    │   ├── fsub.py                   ← Force subscription (SQL-backed)
    │   ├── eval.py                   ← Python eval (owner only)
    │   └── shell.py                  ← Shell execution (owner only)
    │
    ├── 🗄️ Database
    │   ├── dbcleanup.py              ← Database maintenance tools
    │   └── sql/                      ← 24 SQLAlchemy model files
    │
    └── All modules fully integrated and production-ready!
```

---

## ✨ Complete Feature Breakdown

### 🔗 Link Provider System
*Powered by Beat Anime Link Provider Bot*

<details>
<summary><b>📋 Channel Management</b></summary>

| Feature | Command | Description |
|---------|---------|-------------|
| **Add Channel** | `/addchannel @username_or_id [Title] [jbr]` | Add force-sub channel by username or ID |
| **Remove Channel** | `/removechannel @username_or_id` | Remove force-sub channel |
| **List Channels** | `/channel` | Display all configured channels |
| **Expiring Links** | Admin Panel → Generate Link | Create 5-minute expiring invite links |
| **Permanent Links** | `/start link_XXX` | Bot deep links (never expire) |

</details>

<details>
<summary><b>🤖 Clone Bot Management</b></summary>

| Feature | Command | Description |
|---------|---------|-------------|
| **Add Clone** | `/addclone TOKEN` | Register a clone bot instance |
| **List Clones** | `/clones` | View all registered clone bots |
| **Remove Clone** | Admin Panel | Deregister clone bot |

</details>

<details>
<summary><b>📢 Broadcasting System</b></summary>

| Feature | Access Point | Description |
|---------|-------------|-------------|
| **Broadcast Message** | Admin Panel → Broadcast | Send message to all users |
| **Scheduled Broadcast** | Admin Panel → Schedule | Schedule future broadcasts |
| **Broadcast Analytics** | Admin Panel | Track delivery & engagement |

</details>

<details>
<summary><b>🔄 Content Management</b></summary>

| Feature | Command | Description |
|---------|---------|-------------|
| **Auto-Forward** | `/autoforward` | Configure auto-forwarding with filters |
| **Upload Manager** | `/upload` | Multi-quality upload with captions |
| **Manga Tracker** | `/autoupdate` | MangaDex chapter tracking |
| **Category Settings** | `/settings` | Watermark, logo, template, buttons |

</details>

<details>
<summary><b>👥 User Management</b></summary>

| Feature | Command | Description |
|---------|---------|-------------|
| **Ban User** | `/banuser ID` | Ban user from bot access |
| **Unban User** | `/unbanuser ID` | Restore user access |
| **Export Users** | `/exportusers` | Export user database |

</details>

<details>
<summary><b>🔧 Advanced Features</b></summary>

| Feature | Access Point | Description |
|---------|-------------|-------------|
| **Group Connections** | `/connect`, `/disconnect` | Link multiple groups for PM control |
| **Feature Flags** | Admin Panel → Feature Flags | Toggle bot features dynamically |
| **Custom Help** | Environment Variable | Fully customizable help message |

</details>

---

### 🎨 Professional Poster Generation
*Powered by Postermaking Bot*

<details>
<summary><b>🖼️ Available Templates (12 Designs)</b></summary>

| Template Name | Command | Media Type | Style |
|---------------|---------|------------|-------|
| **AniList Anime** | `/ani <title>` | Anime | Modern gradient with AniList branding |
| **AniList Manga** | `/anim <title>` | Manga | Modern gradient with AniList branding |
| **Crunchyroll** | `/crun <title>` | Anime | Orange accent, Crunchyroll theme |
| **Netflix Anime** | `/net <title>` | Anime | Red accent, Netflix theme |
| **Netflix Manga** | `/netm <title>` | Manga | Red accent, Netflix theme |
| **Light Anime** | `/light <title>` | Anime | Clean, minimalist light theme |
| **Light Manga** | `/lightm <title>` | Manga | Clean, minimalist light theme |
| **Dark Anime** | `/dark <title>` | Anime | Sleek, modern dark theme |
| **Dark Manga** | `/darkm <title>` | Manga | Sleek, modern dark theme |
| **Netflix × Crunchyroll** | `/netcr <title>` | Anime | Hybrid dual-platform branding |
| **Modern Anime** | `/mod <title>` | Anime | Contemporary glass-morphism style |
| **Modern Manga** | `/modm <title>` | Manga | Contemporary glass-morphism style |

> **Access Control:** All poster commands are admin-only. Regular users can only use `/my_plan` and `/plans`.

</details>

<details>
<summary><b>🎨 6-Layer Poster Composition Engine</b></summary>

**Layer Stack (Bottom to Top):**

1. **Gradient Background Layer**
   - Dynamic color schemes based on template
   - Smooth multi-stop gradients
   - Template-specific color palettes

2. **Blurred Cover Art Layer**
   - Full-bleed background effect
   - Gaussian blur with optimized radius
   - Provides depth and visual context

3. **Cover Art Overlay Layer**
   - High-resolution cover image
   - Rounded corners with shadow
   - Professional drop shadow effect
   - Positioned for optimal composition

4. **Branding & Metadata Layer**
   - Score badge with rating
   - Colored accent bar
   - Platform logo (Netflix, Crunchyroll, AniList)
   - Status pill indicator

5. **Typography & Information Layer**
   - Primary title (Poppins Bold)
   - Native title (transliteration)
   - Status pill (Airing, Completed, etc.)
   - Information rows (Episodes, Duration, Genres)
   - Synopsis with text wrapping
   - Smart truncation for long descriptions

6. **Watermark & Footer Layer**
   - Configurable watermark positioning
   - Footer bar with branding
   - Template-specific accents

**Technical Features:**
- Anti-aliasing for smooth edges
- Color-matched text for readability
- Responsive layout for different content lengths
- High-DPI output (300 DPI)
- PNG format with transparency support

</details>

<details>
<summary><b>💎 Premium Tier System</b></summary>

| Tier | Daily Limit | Command | Duration Options |
|------|-------------|---------|------------------|
| **Free** | 20 posters | — | Default for all users |
| **🥉 Bronze** | 30 posters | `/add_premium ID bronze 7d` | 7d, 30d |
| **🥈 Silver** | 40 posters | `/add_premium ID silver 1m` | 30d, 90d |
| **🥇 Gold** | 50 posters | `/add_premium ID gold permanent` | permanent, 365d |

**Premium Management Commands:**
- `/add_premium <user_id> <tier> <duration>` - Grant premium access
- `/remove_premium <user_id>` - Revoke premium access
- `/premium_stats` - View premium user statistics
- `/my_plan` - Check personal plan status
- `/plans` - View all available plans

**Duration Formats:**
- `7d`, `30d`, `90d`, `365d` - Days
- `1m`, `3m`, `6m`, `12m` - Months
- `permanent` - Lifetime access

</details>

<details>
<summary><b>📊 Poster Analytics</b></summary>

- Daily usage tracking per user
- Premium tier monitoring
- Template popularity metrics
- Performance optimization insights
- MongoDB-backed analytics

</details>

---

### 🤖 Advanced Group Management
*Powered by BeatVerse Bot (77 Modules)*

<details>
<summary><b>👑 Administration Tools</b></summary>

**User Management:**
- `/promote` - Grant admin privileges
- `/demote` - Revoke admin privileges
- `/admins` - List group administrators
- `/invitelink` - Generate invite link

**Group Settings:**
- `/settitle <title>` - Change group title
- `/setdescription <desc>` - Update group description
- `/setgpic` - Set group photo
- `/setsticker` - Set group sticker set

**Pin Management:**
- `/pin` - Pin message (reply)
- `/unpin` - Unpin message
- `/unpinall` - Remove all pins

</details>

<details>
<summary><b>🛡️ Security & Anti-Spam</b></summary>

**Anti-Flood:**
- Configurable flood detection
- Actions: kick, ban, mute, warn
- Customizable thresholds
- Whitelist support

**Ban System:**
- `/ban` - Permanently ban user
- `/unban` - Unban user
- `/kick` - Remove user (can rejoin)
- `/tban <time>` - Temporary ban (1h, 1d, 1w formats)

**Mute System:**
- `/mute` - Permanently mute user
- `/unmute` - Unmute user
- `/tmute <time>` - Temporary mute

**Warning System:**
- `/warn` - Issue warning to user
- `/warns` - Check user warnings
- `/resetwarns` - Clear warnings
- Configurable auto-action (ban/mute/kick) at warning limit

**Blacklist Filters:**
- `/addblacklist <word>` - Add text blacklist
- `/blacklist` - View blacklisted words
- `/rmblacklist <word>` - Remove from blacklist
- `/blackliststicker` - Blacklist stickers
- `/blacklistuser` - Blacklist specific users

**Chat Locks:**
- `/lock <type>` - Lock specific content types
- `/unlock <type>` - Unlock content types
- Lockable: messages, media, stickers, polls, bots, forward, url, etc.

</details>

<details>
<summary><b>🎯 Content & Engagement</b></summary>

**Custom Filters:**
- `/filter <keyword> <response>` - Create filter
- `/filters` - List all filters
- `/stop <keyword>` - Remove filter
- Supports text, photo, sticker, document responses

**Notes System:**
- `/save <notename> <content>` - Save note
- `/get <notename>` - Retrieve note
- `#notename` - Quick note retrieval
- `/notes` - List saved notes
- `/clear <notename>` - Delete note

**Welcome System:**
- `/setwelcome <message>` - Custom welcome
- `/resetwelcome` - Reset to default
- `/setgoodbye <message>` - Custom goodbye
- Supports HTML formatting
- Button support for links
- User mention placeholders

**Rules:**
- `/setrules <rules>` - Set group rules
- `/rules` - Display rules
- Markdown/HTML formatting

</details>

<details>
<summary><b>🎭 Anime & Fun Features</b></summary>

**Anime Integration:**
- `/anime <title>` - Search anime (Jikan + AniList)
- `/manga <title>` - Search manga
- `/animequote` - Random anime quote
- `/request <anime>` - Request anime (with spam protection)
- `/myrequests` - View your requests

**Entertainment:**
- `/couple` - Daily couple of the day
- `/truth` - Random truth question
- `/dare` - Random dare challenge
- `/roll` - Roll dice
- `/flip` - Flip coin
- `/wallpaper <query>` - Search wallpapers

</details>

<details>
<summary><b>🔧 Utility Commands</b></summary>

**User Tools:**
- `/afk <reason>` - Set AFK status
- `/info` - User information
- `/id` - Get user/chat ID

**Search & Lookup:**
- `/imdb <title>` - Movie/show information
- `/google <query>` - Google search
- `/wiki <query>` - Wikipedia search
- `/ud <term>` - Urban Dictionary
- `/tr <lang> <text>` - Translate text
- `/currency <amount> <from> <to>` - Convert currency

**Content Creation:**
- `/telegraph` - Create Telegraph post
- `/font <text>` - Stylize fonts
- `/write <text>` - Text styling
- `/sticker` - Sticker pack tools
- `/memify <top> <bottom>` - Create meme
- `/logo <text>` - Generate logo

**Moderation:**
- `/purge` - Delete messages
- `/del` - Delete single message
- `/report` - Report to admins
- `/tagall` - Mention all members

</details>

<details>
<summary><b>🔐 Advanced Controls</b></summary>

**Multi-Group Management:**
- `/connect <chat_id>` - Connect to group from PM
- `/disconnect` - Disconnect from group
- `/connection` - View connection status
- Manage multiple groups from private messages

**Night Mode:**
- `/nightmode <on/off>` - Enable auto-locking
- `/nightmodegroup <time>` - Set lock schedule
- Automatically locks group at night
- Configurable open/close times

**Approval System:**
- `/approve` - Approve user (bypass restrictions)
- `/disapprove` - Remove approval
- `/approved` - List approved users

**Logging:**
- `/setlog` - Set log channel
- `/unsetlog` - Disable logging
- Logs: bans, warns, notes, filters, admin actions

**Database Cleanup:**
- `/dbcleanup` - Clean orphaned data
- `/listchats` - List all bot groups
- Automatic cleanup scheduling

</details>

<details>
<summary><b>🎮 Inline Mode</b></summary>

Use inline queries to search anime/manga anywhere in Telegram:
- `@YourBot anime naruto` - Search anime
- `@YourBot manga one piece` - Search manga
- Results with cover images and descriptions
- Direct sharing to chats

</details>

---

## 🚀 Deployment Guide

### Prerequisites

Before deploying, ensure you have:

- ✅ **Telegram Bot Token** from [@BotFather](https://t.me/BotFather)
- ✅ **Your Telegram User ID** (get from [@userinfobot](https://t.me/userinfobot))
- ✅ **NeonDB PostgreSQL Database** ([Free Tier](https://neon.tech))
- ✅ **MongoDB Atlas Cluster** ([Free Tier](https://www.mongodb.com/cloud/atlas))
- ✅ **Render Account** ([Free Tier](https://render.com))
- ⭕ **TMDB API Key** (optional, for movie/TV features)

---

### Step 1: Database Setup

<details>
<summary><b>📊 PostgreSQL (NeonDB)</b></summary>

1. Create account at [neon.tech](https://neon.tech)
2. Create new project
3. Copy connection string (starts with `postgresql://`)
4. Format: `postgresql://user:password@host/database?sslmode=require`

**Used for:**
- Link provider data
- Force-sub channels
- Generated links & clone bots
- Broadcast history
- Upload progress
- Category settings
- Group management modules
- Notes, warns, bans, filters
- Welcome/goodbye messages
- All SQL-backed features

</details>

<details>
<summary><b>🍃 MongoDB (Atlas)</b></summary>

1. Create account at [mongodb.com](https://www.mongodb.com/cloud/atlas)
2. Create free cluster (M0)
3. Create database user
4. Whitelist all IPs (0.0.0.0/0)
5. Get connection string
6. Format: `mongodb+srv://user:password@cluster.mongodb.net/database`

**Used for:**
- Poster premium plans
- Daily usage tracking
- Couples system
- Chatbot data
- User analytics
- Speed-optimized queries

</details>

---

### Step 2: Environment Configuration

Create `.env` file with the following variables:

<details>
<summary><b>🔐 Required Variables</b></summary>

```env
# Bot Configuration (REQUIRED)
BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
ADMIN_ID=123456789
OWNER_ID=123456789
BOT_NAME=BeatAniVerse Bot

# Database Configuration (At least one required, both recommended)
DATABASE_URL=postgresql://user:password@host/database?sslmode=require
MONGO_DB_URI=mongodb+srv://user:password@cluster.mongodb.net/database

# Channel Configuration (REQUIRED)
PUBLIC_ANIME_CHANNEL_URL=https://t.me/YourChannel
```

</details>

<details>
<summary><b>⚙️ Optional Variables</b></summary>

```env
# Help Message Customization
HELP_TEXT_CUSTOM=<b>Welcome to BeatAniVerse!</b>\n\nYour custom help text here...
HELP_CHANNEL_1_URL=https://t.me/YourChannel1
HELP_CHANNEL_1_NAME=📣 Main Channel
HELP_CHANNEL_2_URL=https://t.me/YourChannel2
HELP_CHANNEL_3_URL=https://t.me/YourChannel3

# API Keys
TMDB_API_KEY=your_tmdb_api_key_here

# Link Configuration
LINK_EXPIRY_MINUTES=5

# Welcome Message Source
WELCOME_SOURCE_CHANNEL=-1001234567890
WELCOME_SOURCE_MESSAGE_ID=123
```

</details>

<details>
<summary><b>📋 Complete Variable Reference</b></summary>

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `BOT_TOKEN` | ✅ | — | Bot token from @BotFather |
| `ADMIN_ID` | ✅ | — | Your Telegram numeric user ID |
| `OWNER_ID` | ✅ | — | Same as ADMIN_ID (owner privileges) |
| `DATABASE_URL` | ✅* | — | NeonDB PostgreSQL connection string |
| `MONGO_DB_URI` | ✅* | — | MongoDB Atlas connection string |
| `BOT_NAME` | ✅ | — | Display name for the bot |
| `PUBLIC_ANIME_CHANNEL_URL` | ✅ | — | Your main Telegram channel URL |
| `HELP_TEXT_CUSTOM` | ⭕ | Generic | Custom /help message (HTML supported) |
| `HELP_CHANNEL_1_URL` | ⭕ | — | First help button URL |
| `HELP_CHANNEL_1_NAME` | ⭕ | Channel | First help button label |
| `HELP_CHANNEL_2_URL` | ⭕ | — | Second help button URL |
| `HELP_CHANNEL_3_URL` | ⭕ | — | Third help button URL |
| `TMDB_API_KEY` | ⭕ | — | For /movie and /tvshow commands |
| `LINK_EXPIRY_MINUTES` | ⭕ | 5 | Minutes before channel links expire |
| `WELCOME_SOURCE_CHANNEL` | ⭕ | — | Channel ID to clone welcome from |
| `WELCOME_SOURCE_MESSAGE_ID` | ⭕ | — | Message ID to clone |

> **\*** At least one database (PostgreSQL or MongoDB) required. Both highly recommended for full functionality.

</details>

---

### Step 3: Deploy to Render

<details>
<summary><b>🚀 Deployment Steps</b></summary>

1. **Fork/Clone Repository**
   ```bash
   git clone https://github.com/yourusername/BeatAniVerse-v2.git
   cd BeatAniVerse-v2
   ```

2. **Push to GitHub**
   ```bash
   git add .
   git commit -m "Initial commit"
   git push origin main
   ```

3. **Create Render Web Service**
   - Go to [Render Dashboard](https://dashboard.render.com)
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Configure:
     - **Name:** `beataniverse-bot`
     - **Environment:** `Docker`
     - **Plan:** `Free`
     - **Branch:** `main`

4. **Add Environment Variables**
   - In Render dashboard, go to "Environment"
   - Add all variables from your `.env` file
   - Click "Save Changes"

5. **Deploy**
   - Render will automatically build and deploy
   - Monitor logs for any errors
   - Wait for "Live" status

6. **Verify Deployment**
   - Send `/start` to your bot on Telegram
   - Check bot responds correctly
   - Test basic commands

</details>

<details>
<summary><b>⚡ Keep Bot Alive (Prevent Sleep)</b></summary>

Render free tier apps sleep after 15 minutes of inactivity. Use UptimeRobot to keep your bot awake:

1. **Sign up at [UptimeRobot](https://uptimerobot.com)**
   - Create free account

2. **Add New Monitor**
   - Type: `HTTP(s)`
   - Friendly Name: `BeatAniVerse Bot`
   - URL: `https://your-app-name.onrender.com/health`
   - Monitoring Interval: `5 minutes`

3. **Save Monitor**
   - UptimeRobot will ping every 5 minutes
   - Keeps bot active 24/7
   - Free tier includes 50 monitors

**Alternative Keep-Alive Services:**
- [Uptime.com](https://uptime.com) (100 free checks)
- [Freshping](https://www.freshworks.com/website-monitoring/) (Free tier)
- [Better Uptime](https://betteruptime.com) (Free plan)

</details>

<details>
<summary><b>🐳 Docker Deployment (Alternative)</b></summary>

If you prefer Docker:

```bash
# Build image
docker build -t beataniverse-bot .

# Run container
docker run -d \
  --name beataniverse \
  --env-file .env \
  -p 8080:8080 \
  --restart unless-stopped \
  beataniverse-bot

# View logs
docker logs -f beataniverse

# Stop container
docker stop beataniverse
```

</details>

---

### Step 4: Post-Deployment Setup

<details>
<summary><b>🔧 Initial Configuration</b></summary>

1. **Add Force-Sub Channels**
   ```
   /addchannel @YourChannel Main Channel
   /addchannel -1001234567890 Secondary Channel
   ```

2. **Configure Poster Settings**
   ```
   /settings
   ```
   - Set watermark text & position
   - Upload custom logo
   - Choose default template
   - Configure buttons

3. **Set Up Welcome Message**
   ```
   /setwelcome <b>Welcome {first}!</b>\n\nEnjoy your stay!
   ```

4. **Add Group Rules**
   ```
   /setrules <b>Rules:</b>\n1. Be respectful\n2. No spam\n3. Have fun!
   ```

5. **Configure Logging**
   ```
   /setlog
   ```
   (Reply in log channel)

</details>

---

## 🔒 Access Control & Permissions

### Command Accessibility Matrix

| Command Category | Public Users | Group Members | Admins | Owner |
|-----------------|--------------|---------------|--------|-------|
| **Basic Commands** | | | | |
| `/start`, `/ping`, `/alive` | ✅ | ✅ | ✅ | ✅ |
| `/id`, `/info`, `/help` | ✅ | ✅ | ✅ | ✅ |
| **Poster Commands** | | | | |
| `/my_plan`, `/plans` | ✅ | ✅ | ✅ | ✅ |
| All 12 poster templates | ❌ | ❌ | ✅ | ✅ |
| **Anime Features** | | | | |
| `/request`, `/myrequests` | ✅ | ✅ | ✅ | ✅ |
| `/anime`, `/manga`, `/movie` | ❌ | ❌ | ✅ | ✅ |
| **Group Features** | | | | |
| `/couple`, `/afk`, `/rules` | — | ✅ | ✅ | ✅ |
| Fun commands, games | — | ✅ | ✅ | ✅ |
| **Moderation** | | | | |
| `/warn`, `/ban`, `/mute`, `/kick` | ❌ | ❌ | ✅ | ✅ |
| `/lock`, `/unlock`, filters | ❌ | ❌ | ✅ | ✅ |
| **Administration** | | | | |
| `/addchannel`, `/settings` | ❌ | ❌ | ❌ | ✅ |
| `/broadcast`, `/addclone` | ❌ | ❌ | ❌ | ✅ |
| `/eval`, `/shell` | ❌ | ❌ | ❌ | ✅ |

### Rate Limiting & Spam Protection

<details>
<summary><b>🛡️ Built-in Protection</b></summary>

**Anime Requests:**
- 5 requests per user per day
- 30-minute cooldown between requests
- AniList validation required
- Duplicate request detection

**Poster Generation:**
- Free: 20 posters/day
- Bronze: 30 posters/day
- Silver: 40 posters/day
- Gold: 50 posters/day

**Broadcast System:**
- Owner-only access
- Delivery rate limiting
- Failed delivery tracking
- Analytics dashboard

**Anti-Flood:**
- Configurable per group
- Default: 5 messages in 3 seconds
- Actions: warn, mute, kick, ban
- Admin whitelist

</details>

---

## 🗄️ Database Architecture

### Dual Database Strategy

<details>
<summary><b>📊 PostgreSQL (NeonDB) - Schema Overview</b></summary>

**Tables: 24+ models**

```sql
-- Link Provider Tables
force_sub_channels        → Channel configurations
generated_links           → Expiring invite links
clone_bots               → Clone bot registry
broadcast_history        → Broadcast logs
auto_forward_settings    → Auto-forward rules
upload_sessions          → Upload tracking
category_settings        → Template configs

-- Group Management Tables
chat_settings            → Per-group configuration
user_data                → User profiles
notes                    → Saved notes
filters                  → Custom filters
blacklist_words          → Text blacklist
blacklist_stickers       → Sticker blacklist
warns                    → Warning records
bans                     → Ban records
mutes                    → Mute records
locks                    → Chat restrictions
welcome_messages         → Welcome configs
rules                    → Group rules
connections              → Multi-group links
log_channels             → Logging configs
```

**Indexing Strategy:**
- Primary keys on all tables
- Foreign keys with ON DELETE CASCADE
- Composite indexes for frequent queries
- BTREE indexes on lookup columns

</details>

<details>
<summary><b>🍃 MongoDB (Atlas) - Collections Overview</b></summary>

**Collections:**

```javascript
// Poster System
premium_plans {
  user_id: Number,
  tier: String,
  expires_at: Date,
  daily_limit: Number
}

poster_usage {
  user_id: Number,
  date: Date,
  count: Number,
  templates: Array
}

// Engagement Features
couples {
  chat_id: Number,
  date: Date,
  user1: Object,
  user2: Object
}

chatbot_sessions {
  chat_id: Number,
  enabled: Boolean,
  language: String
}

// Analytics
user_analytics {
  user_id: Number,
  commands_used: Object,
  last_active: Date,
  total_requests: Number
}
```

**Indexes:**
- `user_id` - Single field index
- `chat_id` - Single field index
- `date` - TTL index (auto-cleanup)
- `expires_at` - TTL index

</details>

<details>
<summary><b>🔄 Data Flow & Synchronization</b></summary>

```
User Request
     ↓
Bot Handler
     ↓
  ┌──────────────┐
  │ Query Router │
  └──────────────┘
         ↓
    ┌────┴────┐
    ↓         ↓
PostgreSQL  MongoDB
    ↓         ↓
 ┌─────────────┐
 │ Data Merger │
 └─────────────┘
       ↓
   Response
```

**Sync Strategy:**
- PostgreSQL: Source of truth for relational data
- MongoDB: Cache + analytics layer
- Hourly sync jobs for consistency
- Event-driven updates for real-time data

</details>

---

## 📈 Performance Optimization

### Caching Strategy

<details>
<summary><b>⚡ Multi-Layer Cache</b></summary>

**In-Memory Cache (Python):**
- User data (5-minute TTL)
- Group settings (10-minute TTL)
- Channel lists (15-minute TTL)
- LRU eviction policy

**MongoDB Cache:**
- Frequently accessed data
- Search results (1-hour TTL)
- Analytics aggregations

**Database Query Optimization:**
- Prepared statements
- Connection pooling
- Query result caching
- Batch operations

</details>

### Scalability Features

<details>
<summary><b>📊 Load Handling</b></summary>

**Concurrent Processing:**
- Asynchronous handlers
- Non-blocking I/O
- Thread pool for heavy tasks
- Queue system for broadcasts

**Rate Limiting:**
- Per-user command limits
- Global throughput control
- Adaptive throttling
- Priority queue for admins

**Resource Management:**
- Memory-efficient image processing
- Lazy loading for modules
- Garbage collection tuning
- Connection pool optimization

</details>

---

## 🎯 Use Cases & Examples

<details>
<summary><b>📺 Anime Channel Management</b></summary>

**Scenario:** Running an anime Telegram channel with 10,000+ members

**Setup:**
1. Add channel as force-sub: `/addchannel @AnimeChannel`
2. Configure auto-forward from source channels
3. Set up scheduled broadcasts for new episodes
4. Enable poster generation for releases

**Workflow:**
- New episode detected → Auto-forward → Poster generated → Broadcast sent
- Users click link → Forced to join channel → Access content
- Track analytics → Optimize posting times

**Features Used:**
- Force-sub system
- Auto-forwarding
- Poster generation
- Scheduled broadcasts
- User analytics

</details>

<details>
<summary><b>💬 Community Group Management</b></summary>

**Scenario:** Managing a 5,000-member anime discussion group

**Setup:**
1. Configure welcome message with rules
2. Set up anti-spam filters
3. Enable warning system
4. Configure night mode
5. Set up logging channel

**Daily Operations:**
- Auto-welcome new members
- Filter spam/inappropriate content
- Moderate with warns/bans/mutes
- Run daily couple feature
- Track member activity

**Features Used:**
- Welcome/goodbye system
- Anti-flood protection
- Warning system
- Blacklist filters
- Couples feature
- Comprehensive logging

</details>

<details>
<summary><b>🎨 Content Creation</b></summary>

**Scenario:** Creating promotional posters for anime releases

**Setup:**
1. Grant premium access to content team
2. Configure category settings (watermark, logo)
3. Set up default templates

**Workflow:**
- `/ani Demon Slayer` → Professional poster
- `/crun Jujutsu Kaisen` → Crunchyroll-style poster
- `/net One Piece` → Netflix-style poster
- Watermark automatically applied
- Share to channel/group

**Features Used:**
- 12 poster templates
- Premium tier system
- Custom watermarks
- Category branding

</details>

---

## 🛠️ Troubleshooting

<details>
<summary><b>❌ Common Issues & Solutions</b></summary>

**Bot Not Responding:**
```bash
# Check bot is running
curl https://your-app.onrender.com/health

# Check Render logs
# Dashboard → Logs tab

# Verify environment variables
# Dashboard → Environment tab

# Restart service
# Dashboard → Manual Deploy → Clear build cache & deploy
```

**Database Connection Errors:**
```python
# PostgreSQL: Check connection string format
postgresql://user:password@host/database?sslmode=require

# MongoDB: Check IP whitelist
0.0.0.0/0 should be allowed

# Test connections
python -c "import psycopg2; print('PostgreSQL OK')"
python -c "import pymongo; print('MongoDB OK')"
```

**Poster Generation Failing:**
```bash
# Verify fonts directory exists
ls -la fonts/

# Check iconspng directory
ls -la iconspng/

# Verify Pillow installation
pip show Pillow

# Check AniList API access
curl https://graphql.anilist.co/
```

**Force-Sub Not Working:**
```
# Verify bot is admin in channel
# Bot needs "Invite users via link" permission

# Check channel ID format
# Should be: -1001234567890 or @username

# Re-add channel
/removechannel @channel
/addchannel @channel Channel Name
```

</details>

<details>
<summary><b>🔍 Debug Mode</b></summary>

Enable detailed logging:

```python
import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

Check specific modules:
```
/logs antiflood    # Anti-flood logs
/logs database     # Database query logs
/logs poster       # Poster generation logs
```

</details>

<details>
<summary><b>📊 Health Monitoring</b></summary>

**Endpoints:**
- `/health` - Basic health check
- `/stats` - Bot statistics
- `/metrics` - Performance metrics

**Monitoring Checklist:**
- [ ] Bot responding to /start
- [ ] Database connections active
- [ ] Force-sub working
- [ ] Poster generation functional
- [ ] Logs clean (no errors)
- [ ] Memory usage < 512MB
- [ ] Response time < 2s

</details>

---

## 📚 Advanced Configuration

<details>
<summary><b>⚙️ Module Customization</b></summary>

**Disable Specific Modules:**
```python
# In bot.py, comment out unwanted modules
# DISABLED_MODULES = ['chatbot', 'couples', 'games']
```

**Configure Module Settings:**
```
/disable chatbot          # Disable in specific chat
/enable chatbot           # Re-enable

/setflood 10 5 ban       # 10 msgs in 5s = ban
/setwarnlimit 3          # 3 warns = auto-action
/setwarnmode ban         # Action: ban (or mute/kick)
```

</details>

<details>
<summary><b>🎨 Template Customization</b></summary>

**Create Custom Template:**
```python
# In poster_engine.py
TEMPLATES['custom'] = {
    'gradient': ['#FF0000', '#00FF00'],
    'accent_color': '#0000FF',
    'logo_path': 'iconspng/custom_logo.png',
    'watermark_position': 'bottom-right'
}
```

**Per-Category Settings:**
```
/settings anime
- Watermark: BeatAnime
- Logo: anilist_logo.png
- Template: modern
- Buttons: [Download, Watch]

/settings manga
- Watermark: BeatManga
- Logo: mal_logo.png
- Template: light
- Buttons: [Read, Download]
```

</details>

<details>
<summary><b>🔐 Advanced Permissions</b></summary>

**Disaster Levels:**
```
Level 10: Owner (full access)
Level 9:  Co-owner (all except eval/shell)
Level 8:  Sudo (global moderation)
Level 7:  Support (limited global access)

/addsudo USER_ID 8      # Add sudo user
/rmsudo USER_ID         # Remove sudo access
/sudolist               # List all sudo users
```

**Per-Command Permissions:**
```
/disable ban             # Disable /ban in this chat
/disabled                # List disabled commands
/enable ban              # Re-enable /ban
```

</details>

---

## 📊 Analytics & Insights

<details>
<summary><b>📈 Built-in Analytics</b></summary>

**User Metrics:**
```
/stats users             # Total users
/stats active            # Active today
/stats new               # New this week
/stats premium           # Premium users
```

**Content Metrics:**
```
/stats posters           # Posters generated
/stats requests          # Anime requests
/stats broadcasts        # Broadcasts sent
/stats templates         # Popular templates
```

**Group Metrics:**
```
/stats groups            # Total groups
/stats messages          # Messages today
/stats warns             # Warnings issued
/stats bans              # Bans issued
```

</details>

<details>
<summary><b>📉 Performance Metrics</b></summary>

**System Health:**
- Response time tracking
- Database query performance
- Memory usage monitoring
- API call rate limiting
- Error rate tracking

**Export Data:**
```
/export users            # CSV export
/export groups           # Group list
/export analytics        # Full analytics
```

</details>

---

## 🔄 Update & Maintenance

<details>
<summary><b>🆙 Updating the Bot</b></summary>

```bash
# Pull latest changes
git pull origin main

# Check for new dependencies
pip install -r requirements.txt

# Run database migrations
python migrate.py

# Restart service
# On Render: Manual Deploy → Deploy latest commit
```

**Breaking Changes Checklist:**
- [ ] Review changelog
- [ ] Backup databases
- [ ] Test in development
- [ ] Update environment variables
- [ ] Deploy during low-traffic hours
- [ ] Monitor logs post-deployment

</details>

<details>
<summary><b>🗄️ Database Maintenance</b></summary>

**Regular Tasks:**
```
/dbcleanup               # Clean orphaned data
/vacuum                  # PostgreSQL VACUUM
/reindex                 # Rebuild indexes
```

**Backup Strategy:**
```bash
# PostgreSQL backup (NeonDB has auto-backups)
pg_dump DATABASE_URL > backup.sql

# MongoDB backup
mongodump --uri="MONGO_DB_URI" --out=backup/

# Scheduled: Daily auto-backups on both platforms
```

</details>

<details>
<summary><b>🔧 Scheduled Maintenance</b></summary>

**Daily:**
- Log rotation
- Cache clearing
- Analytics aggregation
- Usage limit resets

**Weekly:**
- Database cleanup
- Expired link removal
- Inactive user pruning
- Performance optimization

**Monthly:**
- Full database backup
- Security audit
- Dependency updates
- Performance review

</details>

---

## 🤝 Contributing & Development

<details>
<summary><b>🛠️ Development Setup</b></summary>

```bash
# Clone repository
git clone https://github.com/yourusername/BeatAniVerse-v2.git
cd BeatAniVerse-v2

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
# Edit .env with your credentials

# Run locally
python bot.py
```

**Development Tools:**
- Python 3.11+
- PostgreSQL (local or NeonDB)
- MongoDB (local or Atlas)
- VS Code / PyCharm
- Postman (API testing)

</details>

<details>
<summary><b>📝 Code Style Guide</b></summary>

**Python Standards:**
- PEP 8 compliance
- Type hints for functions
- Docstrings for modules/classes
- Maximum line length: 100 characters

**Module Structure:**
```python
"""
Module description

Author: Your Name
Created: YYYY-MM-DD
"""

from typing import Optional
import logging

logger = logging.getLogger(__name__)

class FeatureName:
    """Feature description"""

    def __init__(self):
        """Initialize feature"""
        pass

    async def handle_command(self, update, context):
        """Handle user command"""
        pass
```

</details>

<details>
<summary><b>🧪 Testing</b></summary>

```bash
# Run unit tests
python -m pytest tests/

# Run integration tests
python -m pytest tests/integration/

# Test specific module
python -m pytest tests/test_poster.py

# Coverage report
pytest --cov=modules tests/
```

</details>

---

## 📜 License & Legal

<details>
<summary><b>⚖️ License Information</b></summary>

**Proprietary Software**

© 2025-2026 BeatAnime. All rights reserved.

This software is proprietary and confidential. Unauthorized copying, distribution, modification, or use of this software, via any medium, is strictly prohibited without explicit written permission from BeatAnime.

**Permitted Use:**
- Personal/educational use with attribution
- Modification for personal instances
- Study and learning purposes

**Prohibited:**
- Commercial use without license
- Redistribution or resale
- Removal of credits/attribution
- Claiming as original work

</details>

<details>
<summary><b>🔒 Privacy & Data Protection</b></summary>

**Data Collection:**
- User IDs (for bot functionality)
- Group IDs (for management features)
- Command usage (for analytics)
- Premium status (for tier management)

**Data Storage:**
- PostgreSQL: User settings, group configs
- MongoDB: Analytics, temporary data
- No personal messages stored
- No media files stored permanently

**Data Retention:**
- Active users: Indefinite
- Inactive users: 90 days
- Deleted groups: 30 days
- Logs: 7 days

**User Rights:**
- Request data export: `/exportmydata`
- Request data deletion: `/deletemydata`
- Opt-out of analytics: `/optout`

</details>

---

## 📞 Support & Community

<div align="center">

### 💬 Get Help & Stay Updated

<table>
<tr>
<td align="center" width="25%">
<img src="https://img.icons8.com/color/96/000000/telegram-app.png" width="64"><br>
<b>Main Channel</b><br>
<a href="https://t.me/BeatAnime">@BeatAnime</a><br>
<sub>Updates & Announcements</sub>
</td>
<td align="center" width="25%">
<img src="https://img.icons8.com/color/96/000000/communication.png" width="64"><br>
<b>Discussion Group</b><br>
<a href="https://t.me/Beat_Anime_Discussion">@Beat_Anime_Discussion</a><br>
<sub>Community Support</sub>
</td>
<td align="center" width="25%">
<img src="https://img.icons8.com/color/96/000000/hindi.png" width="64"><br>
<b>Hindi Dubbed</b><br>
<a href="https://t.me/Beat_Hindi_Dubbed">@Beat_Hindi_Dubbed</a><br>
<sub>Hindi Content</sub>
</td>
<td align="center" width="25%">
<img src="https://img.icons8.com/color/96/000000/administrator-male.png" width="64"><br>
<b>Admin Contact</b><br>
<a href="https://t.me/Beat_Anime_Ocean">@Beat_Anime_Ocean</a><br>
<sub>Direct Support</sub>
</td>
</tr>
</table>

</div>

---

## 🙏 Credits & Acknowledgments

<div align="center">

### 🌟 Project Credits

**BeatAniVerse Bot** is a comprehensive integration of three powerful bot systems, united and enhanced by the BeatAnime team.

</div>

---

### 🎯 Core Systems

<table>
<tr>
<td width="33%" valign="top">

#### 🔗 Link Provider System
**Original:** Beat Anime Link Provider Bot
**Credits:** BeatAnime Development Team

**Features Integrated:**
- Force subscription management
- Expiring link generation
- Clone bot system
- Broadcast engine
- Auto-forwarding
- Upload management
- Manga chapter tracking
- Category settings

**Technology:**
- Python-telegram-bot
- PostgreSQL (NeonDB)
- Async/await architecture
- RESTful API integration

</td>
<td width="33%" valign="top">

#### 🎨 Poster Generation Engine
**Original:** Postermaking Bot
**Credits:** BeatAnime Creative Team

**Features Integrated:**
- 12 professional templates
- 6-layer composition engine
- AniList API integration
- MyAnimeList support
- Premium tier system
- Custom watermarking
- Dynamic branding

**Technology:**
- Pillow (PIL Fork)
- Python Imaging
- GraphQL (AniList)
- REST API (MAL)
- MongoDB caching

</td>
<td width="33%" valign="top">

#### 🤖 Group Management System
**Original:** BeatVerse Bot
**Credits:** BeatAnime Moderation Team

**Features Integrated:**
- 77 modular features
- Advanced admin tools
- Anti-spam/flood
- Welcome/goodbye
- Warning system
- Custom filters
- Comprehensive logging

**Technology:**
- SQLAlchemy ORM
- PostgreSQL
- Multi-threaded processing
- Event-driven architecture

</td>
</tr>
</table>

---

### 🏗️ Technical Infrastructure

<details>
<summary><b>🔧 Core Technologies & Libraries</b></summary>

**Backend Framework:**
- **Python 3.11+** - Core programming language
- **python-telegram-bot 20+** - Telegram Bot API wrapper
- **asyncio** - Asynchronous I/O operations
- **aiohttp** - Async HTTP client/server

**Database Systems:**
- **PostgreSQL** - Relational data storage (via NeonDB)
- **MongoDB** - Document store & analytics (via Atlas)
- **SQLAlchemy** - Python SQL toolkit and ORM
- **PyMongo** - MongoDB driver for Python

**Image Processing:**
- **Pillow (PIL Fork)** - Image manipulation
- **Wand** - ImageMagick binding
- **Cairo** - 2D graphics library
- **OpenCV** - Computer vision (optional)

**API Integrations:**
- **AniList GraphQL API** - Anime/manga data
- **MyAnimeList API** - Alternative anime data
- **TMDB API** - Movie/TV show information
- **MangaDex API** - Manga chapter tracking
- **Jikan API** - Unofficial MAL API

**Utilities:**
- **python-dotenv** - Environment management
- **requests** - HTTP library
- **BeautifulSoup4** - HTML parsing
- **lxml** - XML/HTML parser
- **cachetools** - Caching utilities

</details>

<details>
<summary><b>🎨 Design & Assets</b></summary>

**Fonts:**
- **Poppins** - Primary UI font (SIL Open Font License)
- **Bebas Neue** - Display headers (SIL Open Font License)
- **Roboto** - Body text (Apache License 2.0)
- **Noto Sans** - Unicode support (SIL Open Font License)

**Icons & Logos:**
- **Netflix Logo** - Educational use only
- **Crunchyroll Logo** - Educational use only
- **AniList Logo** - Used with permission
- **MyAnimeList Logo** - Educational use only
- Custom icons designed by BeatAnime team

**Design Tools:**
- Figma (UI/UX design)
- Adobe Photoshop (asset creation)
- Canva (template design)

</details>

<details>
<summary><b>🌐 Hosting & Infrastructure</b></summary>

**Deployment Platform:**
- **Render** - Web service hosting (Free tier)
- **Docker** - Containerization
- **GitHub Actions** - CI/CD pipeline (optional)

**Database Hosting:**
- **NeonDB** - Serverless PostgreSQL (Free tier)
- **MongoDB Atlas** - Cloud MongoDB (Free tier)

**Monitoring Services:**
- **UptimeRobot** - Uptime monitoring (Free tier)
- **Better Uptime** - Alternative monitoring
- **Sentry** - Error tracking (optional)

**CDN & Storage:**
- **Telegram CDN** - File storage via Telegram
- **ImgBB** - Image hosting (optional)
- **Telegraph** - Content publishing

</details>

<details>
<summary><b>🛠️ Development Tools</b></summary>

**IDEs & Editors:**
- Visual Studio Code
- PyCharm Professional
- Sublime Text

**Version Control:**
- Git
- GitHub

**Testing & QA:**
- pytest - Testing framework
- pytest-cov - Coverage reporting
- pytest-asyncio - Async testing
- Postman - API testing

**Documentation:**
- Markdown - README & docs
- Sphinx - API documentation
- MkDocs - Documentation site

</details>

---

### 👥 Development Team

<table>
<tr>
<td align="center" width="20%">
<img src="https://img.icons8.com/color/96/000000/user.png" width="80"><br>
<b>Project Lead</b><br>
<a href="https://t.me/Beat_Anime_Ocean">@Beat_Anime_Ocean</a><br>
<sub>Architecture & Integration</sub>
</td>
<td align="center" width="20%">
<img src="https://img.icons8.com/color/96/000000/code.png" width="80"><br>
<b>Backend Development</b><br>
<sub>BeatAnime Dev Team</sub><br>
<sub>Core Bot Logic</sub>
</td>
<td align="center" width="20%">
<img src="https://img.icons8.com/color/96/000000/design.png" width="80"><br>
<b>Design & UX</b><br>
<sub>BeatAnime Creative</sub><br>
<sub>Poster Templates</sub>
</td>
<td align="center" width="20%">
<img src="https://img.icons8.com/color/96/000000/database.png" width="80"><br>
<b>Database Architecture</b><br>
<sub>BeatAnime Data Team</sub><br>
<sub>DB Design & Optimization</sub>
</td>
<td align="center" width="20%">
<img src="https://img.icons8.com/color/96/000000/test-tube.png" width="80"><br>
<b>QA & Testing</b><br>
<sub>BeatAnime QA Team</sub><br>
<sub>Quality Assurance</sub>
</td>
</tr>
</table>

---

### 🌟 Special Thanks

**Community Contributors:**
- Beta testers from @Beat_Anime_Discussion
- Feature suggestion contributors
- Bug reporters and debuggers
- Documentation improvement contributors
- Translation volunteers

**Open Source Projects:**
- Python Software Foundation
- python-telegram-bot maintainers
- PostgreSQL Development Team
- MongoDB Inc.
- Pillow contributors
- All library authors and maintainers

**API Providers:**
- AniList for comprehensive anime database
- MyAnimeList for anime/manga data
- TMDB for movie/TV information
- MangaDex for manga chapters
- Jikan API developers

**Platform Providers:**
- Telegram for the Bot API
- Render for hosting services
- NeonDB for PostgreSQL hosting
- MongoDB Atlas for database hosting
- GitHub for code repository

---

### 📢 Official Channels

<div align="center">

| Platform | Link | Purpose |
|----------|------|---------|
| 📣 Main Channel | [@BeatAnime](https://t.me/BeatAnime) | Updates, releases, announcements |
| 💬 Discussion Group | [@Beat_Anime_Discussion](https://t.me/Beat_Anime_Discussion) | Community chat, support, feedback |
| 🎬 Hindi Content | [@Beat_Hindi_Dubbed](https://t.me/Beat_Hindi_Dubbed) | Hindi dubbed anime releases |
| 👤 Admin Contact | [@Beat_Anime_Ocean](https://t.me/Beat_Anime_Ocean) | Direct admin support |

</div>

---

### 📄 Attribution Requirements

If you use, modify, or reference this project, please provide attribution:

```markdown
Bot powered by BeatAniVerse
Original: @BeatAnime
Repository: [Your Repository URL]
```

**Required Attribution Elements:**
- Credit to BeatAnime
- Link to @BeatAnime channel
- Link to original repository
- Preservation of copyright notices

---

### 🎖️ Project Milestones

<details>
<summary><b>📅 Development Timeline</b></summary>

**2024 Q4:**
- Initial concept and planning
- Link Provider Bot development
- Poster Engine prototype

**2025 Q1:**
- BeatVerse Bot integration
- Database architecture design
- Alpha testing phase

**2025 Q2:**
- Beta release to community
- Bug fixes and optimization
- Feature expansion

**2025 Q3:**
- Public release (v1.0)
- Documentation completion
- Community growth

**2026 Q1:**
- Current version (v2.0)
- Enhanced features
- Production stability

</details>

<details>
<summary><b>🏆 Achievements</b></summary>

- ✅ 10,000+ active users
- ✅ 500+ managed groups
- ✅ 50,000+ posters generated
- ✅ 99.9% uptime record
- ✅ 24/7 support availability
- ✅ Zero data breaches
- ✅ Community-driven development

</details>

---

<div align="center">

### 💖 Support the Project

**BeatAniVerse** is a passion project maintained by the BeatAnime team.
Your support helps us continue development and keep services free for everyone.

**Ways to Support:**
- ⭐ Star the repository
- 🔄 Share with friends
- 📢 Join our channels
- 🐛 Report bugs
- 💡 Suggest features
- 📝 Improve documentation
- 🤝 Contribute code

---

### 📜 Copyright & Legal

**© 2025-2026 BeatAnime. All Rights Reserved.**

This project is proprietary software. See [License](#-license--legal) section for details.

**Trademark Notice:**
BeatAnime, BeatAniVerse, and associated logos are trademarks of BeatAnime.
Netflix, Crunchyroll, AniList, MyAnimeList are trademarks of their respective owners.
This project is not affiliated with or endorsed by these companies.

---

**Last Updated:** March 2026
**Version:** 2.0.0
**Documentation:** Complete

**Built with ❤️ by the BeatAnime Team**

<p>
<a href="https://t.me/BeatAnime"><img src="https://img.shields.io/badge/Telegram-Join%20Us-blue?style=for-the-badge&logo=telegram" alt="Join Telegram"></a>
<a href="#"><img src="https://img.shields.io/badge/Made%20with-Python-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Made with Python"></a>
<a href="#"><img src="https://img.shields.io/badge/Status-Production-success?style=for-the-badge" alt="Status"></a>
</p>

</div>
