# Chat Turn Continuity — browser extension prototype

This is a host-specific prototype for the ChatGPT web interface. It stores turn data in the browser profile's IndexedDB and does not send messages to an external server.

## What it does

- Intercepts recognized ChatGPT text-send actions and waits for local journal registration before dispatching the message.
- Stores the exact incoming text, the immediately previous assistant message, conversation/task identifiers, the prior checkpoint reference (currently UNKNOWN/null unless supplied by a future integration), and timestamps.
- Tracks work start, the last assistant message count, and the final assistant response when the DOM observer can confidently identify a new completed response.
- Shows incomplete turns in the extension popup, lets the user copy a recovery prompt, and allows an explicit JSONL export.
- If registration fails, the recognized text send is blocked and the input remains in the composer.
- No background upload, analytics, or external network requests are implemented.

## Install for a local test

1. Download the repository branch archive and unpack it on the Android device.
2. Open `browser://extensions` in Yandex Browser.
3. Enable Developer mode and choose **Load unpacked extension**.
4. Select this folder's `manifest.json`.
5. Open a ChatGPT conversation and test with a harmless short message first. Check the extension popup for the recorded turn.

Yandex documents third-party extension support and developer-mode loading for Android here: https://yandex.com/support/browser-mobile-android-phone/en/personal-settings/extensions

## Critical limitations

- **Not yet validated in a live browser.** CI can validate code syntax and repository contracts, but cannot prove that current ChatGPT DOM selectors, mobile click behavior, extension permissions, or lifecycle timing work on the user's installed Yandex Browser version.
- ChatGPT may change its DOM. The content script uses several known composer/send selectors and a form-submit fallback, but a UI change can prevent capture. Verify the visible extension behavior before relying on it.
- Attachments-only, voice, and other non-text submission paths are outside the current capture contract.
- Assistant output detection is based on DOM observation after generation appears to stop. This is evidence that a final answer was rendered in the client, not a server-side delivery receipt.
- The extension cannot observe hidden model/tool activity, and it cannot reconstruct output that never appeared in the page.
- The prior checkpoint reference is currently recorded as UNKNOWN/null because no canonical checkpoint bridge is connected to the ChatGPT UI.
- IndexedDB is local browser-profile storage, not encrypted secret storage. Protect the device/profile. Export is user-initiated and contains exact conversation text.
- This prototype does not install itself or change browser settings. User installation and a real-device test are required.

## Recovery workflow

Open the extension popup → inspect the incomplete turn → copy the recovery prompt → return to the chat and submit it manually if needed. The prompt includes the exact user instruction, the previous assistant message captured before send, the last recorded state, and the last event. It tells the next assistant to continue from the first unverified milestone rather than repeat completed work.

Do not infer that an incomplete turn means no work occurred. Correlate the journal with Git changes, checkpoint records, CI, and any available artifacts. Do not delete suspected partial files automatically.
