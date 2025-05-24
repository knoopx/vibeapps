import { visit } from "unist-util-visit";

// https://github.com/silvenon/remark-smartypants?tab=readme-ov-file
// https://github.com/akebifiky/remark-simple-plantuml
// https://github.com/s0/remark-code-extra
export default function remarkDefinitionList() {
  return (tree) => {
    visit(tree, "paragraph", (node, index, parent) => {
      const definitions = [];
      let currentTerm = [];
      let currentDef = [];
      let isDefinitionList = false;

      // Helper function to extract all text content from a node tree
      const extractTextContent = (nodes) => {
        let text = '';
        for (const node of nodes) {
          if (node.type === 'text') {
            text += node.value;
          } else if (node.children) {
            text += extractTextContent(node.children);
          }
        }
        return text;
      };

      // Helper function to reconstruct original markdown text from nodes
      const reconstructMarkdown = (nodes) => {
        let text = '';
        for (const node of nodes) {
          if (node.type === 'text') {
            text += node.value;
          } else if (node.type === 'strong') {
            text += '**' + reconstructMarkdown(node.children) + '**';
          } else if (node.type === 'emphasis') {
            text += '*' + reconstructMarkdown(node.children) + '*';
          } else if (node.type === 'inlineCode') {
            text += '`' + node.value + '`';
          } else if (node.children) {
            text += reconstructMarkdown(node.children);
          } else if (node.value) {
            // Handle other node types that have a value property
            text += node.value;
          }
        }
        return text;
      };

      // First pass to determine if this paragraph node contains a definition list
      const fullText = extractTextContent(node.children);
      const lines = fullText.split('\n');
      if (lines.some((line) => /^(.+?)::(.*)$/.test(line) || /^::(.*)$/.test(line))) {
        isDefinitionList = true;
      }

      if (!isDefinitionList) {
        return; // Not a definition list, do nothing
      }

      // Use reconstructed markdown to preserve formatting
      const markdownText = reconstructMarkdown(node.children);
      const markdownLines = markdownText.split('\n');

      // Process the full text to find definition patterns
      markdownLines.forEach((line) => {
        const match = line.match(/^(.+?)::(.*)$/);
        const contMatch = line.match(/^::(.*)$/);

        if (match) {
          // New term and definition
          if (currentTerm.length > 0) {
            definitions.push({
              term: currentTerm,
              definition: currentDef,
            });
          }
          currentTerm = [{ type: "text", value: match[1].trim() }];
          const defValue = match[2].trim();
          currentDef = [{ type: "text", value: defValue }];
        } else if (contMatch && currentTerm.length > 0) {
          // Continuation definition for current term
          // Add space to the first definition part
          if (currentDef.length > 0 && currentDef[0].value && !currentDef[0].value.endsWith(" ")) {
            currentDef[0].value += " ";
          }
          currentDef.push({ type: "text", value: contMatch[1].trim() + " " });
        } else if (currentTerm.length > 0 && line.trim()) {
          // Additional line for current definition
          // Add space to the first definition part
          if (currentDef.length > 0 && currentDef[0].value && !currentDef[0].value.endsWith(" ")) {
            currentDef[0].value += " ";
          }
          currentDef.push({ type: "text", value: line.trim() + " " });
        }
      });

      if (currentTerm.length > 0) {
        definitions.push({
          term: currentTerm,
          definition: currentDef,
        });
      }

      if (isDefinitionList) {
        parent.children.splice(index, 1, {
          type: "dl",
          children: definitions.flatMap(({ term, definition }) => [
            {
              type: "dt",
              children: term,
              data: { hName: "dt" },
            },
            {
              type: "dd",
              children: definition,
              data: { hName: "dd" },
            },
          ]),
          data: { hName: "dl" },
        });
      }
    });
  };
}
