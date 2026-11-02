# 05 · The Timing Booth — `Forensics` · Medium · 100 pts

> The timing booth submits race splits over the crew Wi-Fi, and its login
> still runs over plain HTTP. We grabbed a capture off the air. See what the
> booth was sending.

**Connect:** `http://<CTF-HOST>:8020` — internal wiki **Intranet DFlop**, space **Chronométrage**, page « Capture Wi-Fi de la cabine » (`timing_booth.pcap`). Credentials are on the DécaFlop staff portal — see challenge 01.

Download the capture and recover the credentials the booth used. The password is the flag.

**Flag format:** `TRIATHLON{...}`

<details><summary>Hint 1 (−15)</summary>Open it in Wireshark and look at the HTTP request headers.</details>
<details><summary>Hint 2 (−30)</summary>HTTP Basic Auth sends <code>Authorization: Basic &lt;base64&gt;</code>. Base64-decode it: the format is <code>user:password</code>.</details>
