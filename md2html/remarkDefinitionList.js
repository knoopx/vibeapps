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

      // Process each line while preserving node structure
      node.children.forEach((child) => {
        if (child.type === "text") {
          const lines = child.value.split("\n");
          lines.forEach((line) => {
            const match = line.match(/^(.+?):: (.*)$/);
            if (match) {
              isDefinitionList = true;
              if (currentTerm.length > 0) {
                definitions.push({
                  term: currentTerm,
                  definition: currentDef,
                });
              }
              currentTerm = [{ type: "text", value: match[1].trim() }];
              currentDef = [{ type: "text", value: match[2].trim() }];
            } else if (currentTerm.length > 0 && line.trim()) {
              currentDef.push({ type: "text", value: line.trim() + " " });
            }
          });
        } else {
          if (currentDef.length > 0) {
            currentDef.push(child);
          }
        }
      });

      if (currentTerm.length > 0) {
        definitions.push({
          term: currentTerm,
          definition: currentDef,
        });
      }

      if (isDefinitionList) {
        parent.children[index] = {
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
        };
      }
    });
  };
}
