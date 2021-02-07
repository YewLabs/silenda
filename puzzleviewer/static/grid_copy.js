window.onload=function() {
  grids = document.getElementsByClassName('grid-copy');
  (Array.from(grids)).forEach((grid) => {
    node = document.createElement('div');
    node.setAttribute('class', 'grid-copy-icon');
    node.setAttribute('title', '⌘C or Ctrl-C to copy grid')
    node.oncopy = function(e) {
      e.preventDefault();
      let html = String.raw`<html>
      <body>
      <meta name="generator" content="Sheets"/>`;
      html += grid.outerHTML;
      e.clipboardData.setData('text/plain', '')
      e.clipboardData.setData('text/html', html)
    };
    grid.parentNode.insertBefore(node, grid.nextSibling);
  });
}
