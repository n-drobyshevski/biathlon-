# 12 · Print Your Own — `Web` · Hard · 175 pts

> The audit sweep isn't only about the ERP — DécaFlop also runs public-facing
> tools. One is the finisher certificate generator, which prints the name you
> give it onto a keepsake certificate. It's a little too literal about that name.

**Connect:** `http://<CTF-HOST>:8012`

The name you submit is rendered on the server. Make the server print something
it shouldn't.

**Flag format:** `TRIATHLON{...}`

<details><summary>Hint 1 (−20)</summary>Put <code>{{7*7}}</code> in the name field. If the certificate shows <b>49</b>, the server is evaluating your input as a template (SSTI).</details>
<details><summary>Hint 2 (−40)</summary>This is a Jinja2 template. From a template you can reach the app's configuration object: <code>{{ config }}</code> lists it.</details>
<details><summary>Hint 3 (−70)</summary>The flag is a config key: <code>{{ config['FLAG'] }}</code> (or <code>{{ config.FLAG }}</code>).</details>
