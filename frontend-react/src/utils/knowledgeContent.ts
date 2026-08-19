const ruleHeadingPattern = /^\s*RULE\s*(?:NO\.?\s*)?\d+\s*(?:[:：.．、\-]\s*)?.*$/i
const chineseChapterPrefixPattern = /^\s*第[一二三四五六七八九十百零〇\d]+[章节条款部分篇]\s*(?:[:：.．、\-]\s*)?/
const hierarchicalNumberPrefixPattern = /^\s*(?:\d+(?:\.\d+)+|[一二三四五六七八九十百零〇]+[、.．]|[（(][一二三四五六七八九十百零〇\d]+[）)])\s*/

/**
 * Remove internal document labels only for the end-user preview.
 * The original chunk remains untouched in the search result and technical panel.
 */
export function cleanKnowledgeContent(content: string): string {
  const cleanedLines = content
    .split(/\r?\n/)
    .map((line) => {
      if (ruleHeadingPattern.test(line)) return ''
      return line
        .replace(chineseChapterPrefixPattern, '')
        .replace(hierarchicalNumberPrefixPattern, '')
        .trimEnd()
    })

  return cleanedLines
    .join('\n')
    .replace(/\n{3,}/g, '\n\n')
    .trim()
}
