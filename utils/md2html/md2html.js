#!/usr/bin/env node

import { unified } from "unified";
import rehypeHighlight from "rehype-highlight";
import rehypeDocument from "rehype-document";
import remarkRehype from "remark-rehype";
import remarkGfm from "remark-gfm";
import remarkWikiLink from "remark-wiki-link";
import rehypeStringify from "rehype-stringify";
import remarkParse from "remark-parse";
import remarkFrontmatter from "remark-frontmatter";
import rehypeAutolinkHeadings from "rehype-autolink-headings";
import rehypeSlug from "rehype-slug";
import rehypeRaw from "rehype-raw";
import rehypeFormat from "rehype-format";
import remarkDefinitionList from "./remarkDefinitionList.js";
// import remarkOembed from "remark-oembed";

async function processMarkdown(input) {
  const file = await unified()
    .use(remarkParse)
    .use(remarkDefinitionList)
    .use(remarkGfm)
    .use(remarkFrontmatter, ["yaml", "toml"])
    .use(remarkWikiLink, {
      pageResolver: (pageName) => [pageName.split("/")[-1]],
      hrefTemplate: (permalink) => `note://${permalink}`,
    })
    // .use(remarkOembed) // TODO: makes requests
    .use(remarkRehype, { allowDangerousHtml: true })
    .use(rehypeRaw)
    .use(rehypeSlug)
    .use(rehypeAutolinkHeadings)
    .use(rehypeHighlight)
    .use(rehypeDocument, {
      css: "@@CSS@@",
    })
    .use(rehypeFormat)
    .use(rehypeStringify, { allowDangerousHtml: true })
    .process(input);
  console.log(String(file));
}

// Read from stdin
let inputData = "";

process.stdin.setEncoding("utf8");
process.stdin.on("data", (chunk) => {
  inputData += chunk;
});

process.stdin.on("end", () => {
  processMarkdown(inputData).catch((err) => {
    console.error(`Error: ${err.message}`);
    process.exit(1);
  });
});
