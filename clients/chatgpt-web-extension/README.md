# Chat Turn Continuity — browser extension prototype

This is a host-specific prototype for the ChatGPT web interface. It stores turn data in the browser profile's IndexedDB and does not send messages to an external server.

## What it does

- Intercepts recognized ChatGPT text-send actions and waits for local journal registration before dispatching the message.
- Stores the exact incoming text, the immediately previous assistant message, conversation/task identifiers, the prior checkpoint reference (currently UNKNOWN/null unless supplied by a future integration), and timestamps.
- Tracks work start, the last assistant message count, and the final assistant response when the DOM observer can confidently identify a new completed response.
- Shows incomplete turns and builds two rolling context windows from locally captured turns: the last five completed pairs globally and the last five completed pairs for the active ChatGPT conversation.
- Lets the user explicitly copy a compact recovery context from the popup. Overlapping pairs are included once and labeled with both window memberships.
- Allows an explicit JSONL export.
- If registration fails, the recognized text send is blocked and the input remains in the composer.
- No background upload, analytics, or external network requests are implemented.

## Install for a local test

1. Download the repository branch archive and unpack it on the Android device.
2. Open `browser://extensions` in Yandex Browser.
3. Enable Developer mode and choose **Load unpacked extension**.
4. Select this folder's `manifest.json`.
5. Open a ChatGPT conversation and test with a harmless short message first. Check the extension popup for the recorded turn.

Yandex documents third-party extension support and developer-mode loading for Android here: https://yandex.com/support/browser-mobile-android-phone/en/personal-settings/extensions

## Optional local attachment-library bridge

The popup can explicitly import a file into the private project library and link the resulting reference to a recorded turn. This is a **manual second selection** of the file; it does not read the file already selected inside ChatGPT, and it does not upload automatically.

1. Run the bridge on the **same device** as the browser. It binds to loopback only:
   ```sh
   python3 -c "import secrets; print(secrets.token_urlsafe(32))" > rima-attachment-token.txt
   chmod 600 rima-attachment-token.txt
   python3 tools/project_attachment_adapter.py --token-file rima-attachment-token.txt --allow-origin chrome-extension://YOUR_EXTENSION_ID --allow-project AGENT_MEMORY_SYSTEM
   ```
2. Open the extension popup. Copy the exact extension origin shown there into `--allow-origin` (restart the bridge if it changes). Enter the explicit project ID and the same token in the popup, then save settings.
3. Open the ChatGPT conversation containing the already-sent message, open the popup, select the exact source turn and reselect the same file from device storage. Choose **Сохранить вложение в библиотеку**.
4. The popup sends file bytes to `127.0.0.1:8766` only. The bridge stores a project-scoped SHA-256 object outside the repository, and the extension records only reference metadata on the selected turn.

The bridge accepts files up to 25 MiB. The token is stored in the browser profile's local extension storage, which is not encrypted secret storage. Do not expose the token, bind the service to a network interface, or add broad/untrusted origins to the allowlist. The server rejects requests without bearer authentication and explicit project/conversation/turn provenance. Live device acceptance is still required.

## Critical limitations

- **Not yet validated in a live browser.** CI can validate code syntax and repository contracts, but cannot prove that current ChatGPT DOM selectors, mobile click behavior, extension permissions, or lifecycle timing work on the user's installed Yandex Browser version.
- ChatGPT may change its DOM. The content script uses several known composer/send selectors and a form-submit fallback, but a UI change can prevent capture. Verify the visible extension behavior before relying on it.
- Attachments-only, voice, and other non-text submission paths are outside the current capture contract. The extension does not automatically capture the file already attached inside ChatGPT. A separate authenticated loopback bridge is wired to a manual popup import workflow: the user reselects the file, explicitly chooses a project and source turn, and only reference metadata is linked into the dialogue journal. No project is inferred automatically.
- Assistant output detection is based on DOM observation after generation appears to stop. This is evidence that a final answer was rendered in the client, not a server-side delivery receipt.
- The extension cannot observe hidden model/tool activity, and it cannot reconstruct output that never appeared in the page.
- The prior checkpoint reference is currently recorded as UNKNOWN/null because no canonical checkpoint bridge is connected to the ChatGPT UI.
- IndexedDB is local browser-profile storage, not encrypted secret storage. Protect the device/profile. Export is user-initiated and contains exact conversation text.
- This prototype does not install itself or change browser settings. User installation and a real-device test are required.

## Recovery workflow

Open the extension popup → use “Скопировать контекст диалога” to copy the two rolling windows for the active conversation → paste that context into the new/current ChatGPT chat when continuity is needed. For an interrupted turn, inspect the incomplete turn and copy its recovery prompt separately. The window context is copied only after an explicit click; it is not injected into or sent with the user's message automatically.

Do not infer that an incomplete turn means no work occurred. Correlate the journal with Git changes, checkpoint records, CI, and any available artifacts. Do not delete suspected partial files automatically.
