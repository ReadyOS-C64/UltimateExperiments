# Documentation build and GitHub Pages

`DOCS/` is the publishable static documentation tree for Ultimate Experiments. It includes full Markdown and HTML references, ReadyFS screenshot walkthroughs, C77 galleries, and copies of the three committed main D81s. It excludes video, log directories, agent working notes, firmware checkouts and external website source repositories.

## Build and validate

From the repository root, with Node.js 20 or newer and Python 3:

```sh
npm ci
npm run build:docs
npm run check:docs
```

The builder reads the project READMEs, `ReadyFS/docs/`, `ReuSQL64/docs/`, C77 screenshots/assets, and the retained walkthrough Markdown/screenshots under `DOCS/readyfs/tours/`. It does not need the ignored external demo-site checkout. Update a reference in its project source and rebuild rather than editing its generated copy. The two walkthroughs are maintained directly in `DOCS/readyfs/tours/`.

Both generated HTML and copied Markdown are committed so a checkout already contains a readable site. The renderer rewrites local document links for HTML, gives headings stable anchors, and adds common navigation. `npm run check:docs` checks local destinations and anchors, rejects video/media dependencies and personal home paths, and verifies the D81 downloads match their project originals.

To preview over HTTP:

```sh
python3 -m http.server 8765 --directory DOCS
```

Open `http://localhost:8765/`. The site uses relative URLs so it works beneath a GitHub repository path as well as a custom domain.

## Enable GitHub Pages

1. Push the repository and these commits to GitHub. This checkout has no remote configured, so no repository or public deployment has been created automatically.
2. In **Settings → Pages → Build and deployment**, choose **GitHub Actions**.
3. Merge the documentation to `main`, or run **Publish documentation** manually from the branch you want to publish. Check that the `github-pages` environment permits that branch.
4. The workflow installs the pinned Markdown dependency, rebuilds and validates `DOCS/`, uploads only that folder, and deploys it. Its deployment output supplies the real website URL.

The workflow triggers on relevant pushes to `main` and supports manual dispatch. Pull requests run a separate validation workflow without deployment. It does not publish the entire repository tree or fetch the independently managed demo websites.

GitHub's [custom Pages workflow documentation](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages) describes the deployment permissions, artifact and environment setup used here. No Jekyll processing is required; `.nojekyll` is included. The existing externally hosted ReadyFS demonstration remains independent.

## Evidence and privacy

Screenshots and tour commands preserve historical test fixture names. They are examples, not locations to reuse for writes. Current scope and the deletion of old raw logs are explained in the [ReadyFS acceptance summary](readyfs/READYFS_ACCEPTANCE.md). Publishing this site does not remove personal information from older Git commits or change commit author metadata.
