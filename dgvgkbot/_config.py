VERSION = "4.2.0"

# MINECRAFT
# -----------------
MC_SERVER_IP = "95.216.191.34"
MC_SERVER_PORT = 25565

# PATHS
# -----------------
BLACKLIST_PATH = "db/blacklist.json"
DB_DIR = "db"
TRUSTED_DIR = f"{DB_DIR}/access"
TRUSTED_PATH = f"{TRUSTED_DIR}/trusted.json"
STATS_DIR = "stats"

# COGS
# -----------------

# Nothing here


# DOWNLOADS
# -----------------
MAX_DL_SIZE = 25_000_000 # 25 MB
DOWNLOADS_ALLOWED = True


# GUILDS
# -----------------
TEST_SERVER_ID = 340921036201525248
DGVGK_SERVER_ID = 178865018031439872
PFM_SERVER_ID = 133332608296681472


# CHANNELS
# -----------------
# Image rehosting
IMAGE_CHANNEL_ID = 549649397420392567 

# General log
LOG_CHANNEL_ID = 340921036201525248

# Error log
ERROR_CHANNEL_ID = 604388280200593411

# File download log
DOWNLOAD_CHANNEL_ID = 563312629045788692

# Joining/leaving guilds log
GUILD_HISTORY_CHANNEL = 565674480660119592 

# Channel to use as base for ctx (see BaseCog.get_command_invocation_ctx())
COMMAND_INVOCATION_CHANNEL = 584386122004561920 


# USERS
# -----------------
OWNER_ID = 103890994440728576 # Replace with own User ID
AUTHOR_MENTION = f"<@{OWNER_ID}>" # Creates an @BOT_AUTHOR mention.




# ARGUMENTS
# -----------------
YES_ARGS = ["y", "yes", "+", "ja", "si", "True", "true"]
NO_ARGS = ["n", "no", "-", "nei", "False", "false"]
ALL_ARGS = ["all", "everyone", "global"]