# QFap Adds

Adds **Enhanced General Ledger**. The Python report directly executes ERPNext General Ledger and only enriches presentation data.

## Install

```bash
cd ~/frappe-bench
bench get-app qfap_adds https://github.com/SalahAddinAbdo/qfap_adds.git
bench --site YOUR-SITE install-app qfap_adds
bench execute qfap_adds.scripts.sync_general_ledger.sync
bench build --app qfap_adds
bench --site YOUR-SITE migrate
bench --site YOUR-SITE clear-cache
bench restart
```

Run the sync command after every ERPNext upgrade, then commit the regenerated JS/HTML if Git is the source of truth.
