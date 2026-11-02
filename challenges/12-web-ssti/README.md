# 12 · Print Your Own — `Web` · Hard · 175 pts

> DécaFlop lets finishers generate a certificate with their name on it. The
> generator is a little too literal about the name you give it.

**Connect:** `http://<CTF-HOST>:8012`

The name you submit is rendered on the server. Make the server print something
it shouldn't.

**Flag format:** `TRIATHLON{...}`

<details><summary>Hint 1 (−20)</summary>Put <code>{{7*7}}</code> in the name field. If the certificate shows <b>49</b>, the server is evaluating your input as a template (SSTI).</details>
<details><summary>Hint 2 (−40)</summary>This is a Jinja2 template. From a template you can reach the app's configuration object: <code>{{ config }}</code> lists it.</details>
<details><summary>Hint 3 (−70)</summary>The flag is a config key: <code>{{ config['FLAG'] }}</code> (or <code>{{ config.FLAG }}</code>).</details>
