# Changelog

## 1.0.1

- Installs from a zip attached to each release, so HACS shows how often it has been downloaded.
  Nothing else changes in how it works.
- Needs Home Assistant 2025.4 or later, as VirtuHome does; HACS won't offer it to an older one.

## 1.0.0

- First release. The licence key, free trials, downloading and checking the extensions, and the
  automations they add from their signed blueprints move here from VirtuHome, which since 0.18 has
  no licence code of its own and gets its extensions from integrations like this one.
- A licence entered in VirtuHome 0.17 or earlier carries on: the key, trials, extensions and their
  automations, with nothing to enter again.
- Sets itself up once installed and Home Assistant restarted; won't start beside a VirtuHome older
  than 0.18, and says so in Repairs.
- Edit → Extras in VirtuHome shows the licence, trials and the extensions there are, as before;
  Check my setup and Repairs say when the licence couldn't renew or a trial ended. English, German
  and Dutch.
