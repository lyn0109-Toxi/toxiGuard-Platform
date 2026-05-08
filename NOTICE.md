# Notices and Third-Party Materials

ToxiGuard-Platform uses open-source software and public regulatory/scientific
data sources. These materials remain subject to their own licenses, terms, and
use policies.

## Python Packages

- Streamlit: Apache-2.0
- requests: Apache-2.0
- pandas: BSD-3-Clause
- NumPy: BSD-3-Clause and other permissive notices in its distribution
- RDKit: BSD-3-Clause
- Pillow: MIT-CMU

Package versions are controlled through `requirements.txt` and the deployment
environment. Keep this notice current when dependencies are added.

## Fonts

The app imports Google Fonts:

- Outfit
- JetBrains Mono

Google Fonts are generally distributed under open font licenses such as the SIL
Open Font License or Apache License, depending on the specific font. Do not
bundle modified font files unless their license terms are reviewed.

## Public Regulatory and Scientific Sources

The platform links to and/or queries public resources including:

- FDA guidance pages and FDA databases
- openFDA APIs
- FDA Orange Book and FDA Dissolution Methods Database links
- PubChem PUG REST
- NIH/NCI Chemical Identifier Resolver
- ICH guideline references hosted by regulatory agencies

These sources are used for decision support, traceability, and source review.
No FDA endorsement, approval, certification, or affiliation is implied.

## USP, EP, and Pharmacopeial References

USP, EP, and other pharmacopeial materials may be protected by copyright,
database rights, contract terms, or subscription/license restrictions. This
repository must not include copied monograph text, proprietary impurity tables,
official limits, official methods, or licensed compendial content unless the
repository owner has the required rights.

The app should use USP/EP references as discovery links and should instruct
users to verify final requirements against the current official licensed
monograph.

## Image and Visual Assets

See `ASSET_ATTRIBUTION.md` for bundled image attribution and usage status.

## No Trademark Endorsement

Names such as FDA, USP, EP, ICH, PubChem, NIH, NCI, Streamlit, RDKit, and
Google are used only to identify sources, technologies, or guidelines. Their
use does not imply endorsement or sponsorship.
