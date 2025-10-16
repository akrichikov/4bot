from __future__ import annotations

# Centralized selectors with stable-first strategy.
# Profile nav anchor (robust to UI variants). Prefer stable data-testid where available,
# but retain aria-label fallbacks for older layouts.
PROFILE_ANCHOR = (
    "a[role='link'][data-testid='AppTabBar_Profile_Link']",
    "a[aria-label='Profile']",
    "a[aria-label='Profile menu']",
)

# Login flow
LOGIN_USERNAME = "input[name='text'], input[autocomplete='username']"
LOGIN_NEXT = "div[role='button'][data-testid='LoginForm_Login_Button'], div[role='button'][data-testid='ocfEnterTextNextButton'], div[role='button'][data-testid='next_button']"
LOGIN_PASSWORD = "input[name='password'], input[autocomplete='current-password']"
LOGIN_SUBMIT = "div[role='button'][data-testid='LoginForm_Login_Button'], div[role='button'][data-testid='LoginForm_Submit_Button'], div[role='button'][data-testid='ocfContinueButton']"
LOGIN_2FA = "input[name='text'][inputmode='numeric']"

# Compose
COMPOSE_URL = "/compose/post"
COMPOSE_TEXTBOX = (
    "div[role='textbox'][data-testid^='tweetTextarea_']",
    "div[role='textbox'][data-testid='tweetTextarea_0']",
    "div[contenteditable='true'][role='textbox']",
)
COMPOSE_SUBMIT = (
    "div[role='button'][data-testid='tweetButtonInline']",
    "div[role='button'][data-testid='tweetButton']",
    "button[data-testid='tweetButton']",
)
COMPOSE_OPENERS = (
    "div[role='button'][data-testid='SideNav_NewTweet_Button']",
    "a[aria-label='Post']",
    "a[aria-label='Tweet']",
)

# Feed (inline) composer hitbox/textbox hints
FEED_COMPOSER_HITBOX = (
    "div[aria-label^='What\u2019s happening']",
    "div[aria-label^='What\'s happening']",
    "div[aria-label='Tweet text']",
)

# Tweet page actions
LIKE_BUTTON = "div[data-testid='like'], button[data-testid='like']"
RETWEET_BUTTON = "div[data-testid='retweet']"
RETWEET_CONFIRM = "div[role='menuitem'][data-testid='retweetConfirm'], div[role='menuitem'][data-testid='retweetConfirm']"
REPLY_BUTTON = "div[data-testid='reply'], button[data-testid='reply']"
REPLY_TEXTBOX = COMPOSE_TEXTBOX
REPLY_SUBMIT = COMPOSE_SUBMIT

# Follow/Unfollow (on profile page)
FOLLOW_BUTTON = (
    "div[data-testid='placementTracking'] div[role='button'][data-testid='userActions-follow']",
    "div[role='button'][data-testid='follow']",
)
UNFOLLOW_BUTTON = (
    "div[role='button'][data-testid='userActions-unfollow']",
    "div[role='button'][data-testid='unfollow']",
)

# Idempotent state markers
UNLIKE_BUTTON = "div[data-testid='unlike']"
UNRETWEET_BUTTON = "div[data-testid='unretweet']"

# DMs
MESSAGE_BUTTON = "div[role='button'][data-testid='sendDMFromProfile'], a[aria-label='Message'], a[aria-label^='Message']"
DM_TEXTBOX = (
    "div[role='textbox'][data-testid='dmComposerTextInput']",
    "textarea[data-testid='dmComposerTextInput']",
)
DM_SEND = "div[role='button'][data-testid='dmComposerSendButton'], button[data-testid='dmComposerSendButton']"

# Toasts / alerts (used for action confirmations)
TOAST_REGION = (
    "div[role='alert']",
    "div[role='status']",
    "div[data-testid='toast']",
    "section[role='alert']",
    "div[aria-live='polite']",
)

# Tweet text container(s) for content confirmation
TWEET_TEXT_SELECTORS = (
    "div[data-testid='tweetText']",
    "article div[lang]",
)
