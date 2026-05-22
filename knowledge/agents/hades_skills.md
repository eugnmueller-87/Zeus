# Hades — Compliance Intelligence Skills

## Mission
Hades is the guardian of legal and ethical boundaries. Every signal that reaches the trading pipeline must pass Hades first. A single OFAC violation or sanctioned-entity trade can result in regulatory action, account closure, and criminal liability. Hades must be strict, fast, and auditable.

## OFAC Sanctions Screening
The Office of Foreign Assets Control (US Treasury) maintains the Specially Designated Nationals (SDN) list. Trading in securities of SDN entities is illegal for US persons and carries extraterritorial enforcement.

German residents are subject to EU sanctions law (not OFAC directly) but IBKR as a US-based broker enforces OFAC globally.

Key entities to block (update this list regularly from official sources):
- Russian state entities: Sberbank, Rosneft, Gazprom, Novatek, Rusal, VTB, Sovcomflot
- Iranian entities: NIOC, Bank Melli, Bank Saderat
- North Korean entities: any North Korean state company
- Venezuelan entities: PDVSA and affiliates

Rule: if any entity on the SDN list appears in the signal text (supplier name, headline, summary), KILL the signal immediately. Log the match for audit.

## EU-Specific Sanctions (critical for German residents)
EU sanctions are implemented via EU regulations and enforced by national authorities (BaFin in Germany).
EU sanctions often differ from OFAC — some entities may be on EU list but not OFAC, or vice versa.

Current EU sanction regimes to check:
- Russia sanctions (EU Regulation 833/2014 and amendments): comprehensive list including Sberbank, VTB, Rossiya Bank
- Belarus sanctions: Belarusian state entities
- Myanmar, Iran, Syria, North Korea: maintain blocklists per EU Official Journal updates

Hades should be updated with fresh EU sanctions data at minimum monthly.

## ESG Filtering
Environmental, Social, Governance filters protect against reputational and regulatory risk.

Hard ESG blocks (kill signal):
- Tobacco production companies
- Cluster munition and landmine manufacturers
- Coal mining companies (EU taxonomy: excluded)
- Companies with active LkSG (German Supply Chain Due Diligence Act) violations

Soft ESG flags (downgrade severity, reduce position size):
- Companies under ESG investigation
- Companies with recent significant environmental incidents
- Companies with known labour rights violations

## LkSG — German Supply Chain Due Diligence Act
Effective 2023 for companies >3000 employees, 2024 for >1000 employees.
German companies must ensure their supply chains are free from human rights violations.
Any signal suggesting a ZEUS-traded company has LkSG violations → ESG flag, compliance_score reduced to 0.4.

## Compliance Score Calibration
1.0 — Clean: no flags, no issues
0.8 — Minor flag: ESG soft flag, non-critical concern
0.4 — Major flag: ESG hard flag, downgraded but not killed
0.0 → KILL: OFAC hit, EU sanctions match, blocked ticker

## Audit Trail
Every Hades decision — pass or kill — must be logged with:
- Signal ID
- Check performed (OFAC, ESG, ticker)
- Result (pass/kill/downgrade)
- Specific match (which entity, which sector)
- Timestamp

This audit trail is required for regulatory compliance and is written to the knowledge base.

## Staying Current
Sanctions lists change. Major geopolitical events can add hundreds of entities overnight (e.g. Russia 2022).
Hades should be updated within 24 hours of any major new sanctions package.
Future enhancement: pull OFAC SDN list via API (https://sanctionslist.ofac.treas.gov/Home/SdnList) on a weekly schedule.
