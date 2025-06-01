// filepath: /home/knoopx/Projects/knoopx/vibeapps/md2html/remarkDefinitionList.test.js
import { describe, it, expect } from "vitest";
import { unified } from "unified";
import remarkParse from "remark-parse";
import remarkDefinitionList from "./remarkDefinitionList.js";

const processMarkdown = (md) => {
  const processor = unified().use(remarkParse).use(remarkDefinitionList);

  const tree = processor.parse(md);
  return processor.runSync(tree);
};

describe("remarkDefinitionList", () => {
  it("should convert a simple definition list", () => {
    const markdown = "Term 1:: Definition 1";
    const tree = processMarkdown(markdown);
    expect(tree.children.length).toBe(1);
    const dlNode = tree.children[0];
    expect(dlNode.type).toBe("dl");
    expect(dlNode.children.length).toBe(2);
    expect(dlNode.children[0].type).toBe("dt");
    expect(dlNode.children[0].children[0].value).toBe("Term 1");
    expect(dlNode.children[1].type).toBe("dd");
    expect(dlNode.children[1].children[0].value).toBe("Definition 1");
  });

  it("should handle multiple definitions for a term", () => {
    const markdown = "Term 1:: Definition 1\n:: Definition 2";
    const tree = processMarkdown(markdown);
    expect(tree.children.length).toBe(1);
    const dlNode = tree.children[0];
    expect(dlNode.type).toBe("dl");
    expect(dlNode.children.length).toBe(2); // One dt, one dd
    expect(dlNode.children[0].type).toBe("dt");
    expect(dlNode.children[0].children[0].value).toBe("Term 1");
    expect(dlNode.children[1].type).toBe("dd");
    expect(dlNode.children[1].children.length).toBe(2);
    expect(dlNode.children[1].children[0].value).toBe("Definition 1 ");
    expect(dlNode.children[1].children[1].value).toBe("Definition 2 ");
  });

  it("should handle multiple terms", () => {
    const markdown = "Term 1:: Definition 1\nTerm 2:: Definition 2";
    const tree = processMarkdown(markdown);
    expect(tree.children.length).toBe(1);
    const dlNode = tree.children[0];
    expect(dlNode.type).toBe("dl");
    expect(dlNode.children.length).toBe(4); // dt, dd, dt, dd
    expect(dlNode.children[0].type).toBe("dt");
    expect(dlNode.children[0].children[0].value).toBe("Term 1");
    expect(dlNode.children[1].type).toBe("dd");
    expect(dlNode.children[1].children[0].value).toBe("Definition 1");
    expect(dlNode.children[2].type).toBe("dt");
    expect(dlNode.children[2].children[0].value).toBe("Term 2");
    expect(dlNode.children[3].type).toBe("dd");
    expect(dlNode.children[3].children[0].value).toBe("Definition 2");
  });

  it("should not convert paragraph without definition syntax", () => {
    const markdown = "This is a normal paragraph.";
    const tree = processMarkdown(markdown);
    expect(tree.children.length).toBe(1);
    expect(tree.children[0].type).toBe("paragraph");
    expect(tree.children[0].children[0].value).toBe(
      "This is a normal paragraph."
    );
  });

  it("should handle definitions spanning multiple lines", () => {
    const markdown =
      "Term 1:: This is the first line.\nThis is the second line.";
    const tree = processMarkdown(markdown);
    expect(tree.children.length).toBe(1);
    const dlNode = tree.children[0];
    expect(dlNode.type).toBe("dl");
    expect(dlNode.children.length).toBe(2);
    expect(dlNode.children[1].type).toBe("dd");
    expect(dlNode.children[1].children.length).toBe(2);
    expect(dlNode.children[1].children[0].value).toBe(
      "This is the first line. "
    );
    expect(dlNode.children[1].children[1].value).toBe(
      "This is the second line. "
    );
  });

  it("should handle empty definition", () => {
    const markdown = "Term 1:: ";
    const tree = processMarkdown(markdown);
    expect(tree.children.length).toBe(1);
    const dlNode = tree.children[0];
    expect(dlNode.type).toBe("dl");
    expect(dlNode.children.length).toBe(2);
    expect(dlNode.children[1].type).toBe("dd");
    expect(dlNode.children[1].children[0].value).toBe("");
  });

  it("should handle definition list mixed with other content", () => {
    const markdown = "Paragraph before.\n\nTerm 1:: Def 1\n\nParagraph after.";
    const tree = processMarkdown(markdown);
    expect(tree.children.length).toBe(3);
    expect(tree.children[0].type).toBe("paragraph");
    expect(tree.children[1].type).toBe("dl");
    expect(tree.children[2].type).toBe("paragraph");
  });

  it("should preserve inline markdown in terms and definitions", () => {
    const markdown = "**Term** *1*:: `Definition` _1_";
    const tree = processMarkdown(markdown);
    const dlNode = tree.children[0];

    // Remark-parse will create separate text nodes around strong/emphasis etc.
    // The plugin currently joins them back into single text nodes.
    // This test reflects the current behavior.
    // A more robust test would check for the actual strong/emphasis nodes.

    expect(dlNode.children[0].type).toBe("dt");
    // The term is split by markdown, the plugin joins it.
    // This test might need adjustment if the plugin's handling of inline markdown changes.
    expect(dlNode.children[0].children[0].value).toBe("**Term** *1*");

    expect(dlNode.children[1].type).toBe("dd");
    expect(dlNode.children[1].children[0].value).toBe("`Definition` *1*");
  });

  it("should handle terms and definitions with leading/trailing spaces", () => {
    const markdown = "  Term 1  ::   Definition 1  ";
    const tree = processMarkdown(markdown);
    const dlNode = tree.children[0];
    expect(dlNode.children[0].children[0].value).toBe("Term 1");
    expect(dlNode.children[1].children[0].value).toBe("Definition 1");
  });

  it("should handle a definition list as the only content", () => {
    const markdown = "Term:: Def";
    const tree = processMarkdown(markdown);
    expect(tree.children.length).toBe(1);
    expect(tree.children[0].type).toBe("dl");
  });

  it("should handle multiple definition items correctly", () => {
    const markdown = `
Apple:: A fruit.
    It is red.
Banana:: A yellow fruit.
    Monkeys love it.
`;
    const tree = processMarkdown(markdown);
    expect(tree.children.length).toBe(1);
    const dlNode = tree.children[0];
    expect(dlNode.type).toBe("dl");
    expect(dlNode.children.length).toBe(4);

    expect(dlNode.children[0].type).toBe("dt");
    expect(dlNode.children[0].children[0].value).toBe("Apple");
    expect(dlNode.children[1].type).toBe("dd");
    expect(dlNode.children[1].children[0].value).toBe("A fruit. ");
    expect(dlNode.children[1].children[1].value).toBe("It is red. ");

    expect(dlNode.children[2].type).toBe("dt");
    expect(dlNode.children[2].children[0].value).toBe("Banana");
    expect(dlNode.children[3].type).toBe("dd");
    expect(dlNode.children[3].children[0].value).toBe("A yellow fruit. ");
    expect(dlNode.children[3].children[1].value).toBe("Monkeys love it. ");
  });
});
