<?xml version="1.0" encoding="UTF-8"?>
<!--
Transform qna.xml file into HTML format
PvNiekerk
-->
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
<xsl:output method="html" version="4.0" encoding="UTF-8" indent="yes"/>
<xsl:template match="/archive/org.sakaiproject.qna">
<html>
    <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no" />

        <link rel="stylesheet" href="/shared/HTML-Template-Library/HTML-Templates-V3/_assets/thirdpartylib/bootstrap-4.3.1/css/bootstrap.min.css" />
        <link rel="stylesheet" href="/shared/HTML-Template-Library/HTML-Templates-V3/_assets/thirdpartylib/fontawesome-free-5.9.0-web/css/all.min.css" />

        <link type="text/css" rel="stylesheet" href="/shared/HTML-Template-Library/HTML-Templates-V3/_assets/css/styles.min.css" />
        <link type="text/css" rel="stylesheet" href="/shared/HTML-Template-Library/HTML-Templates-V3/_assets/css/custom.min.css" />

        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@4.3.1/dist/css/bootstrap.min.css" integrity="sha384-ggOyR0iXCbMQv3Xipma34MD+dH/1fQ784/j6cY/iJTQUOhcWr7x9JvoRxT2MZw1T" crossorigin="anonymous" />
    </head>
<body>
  <div id="content" class="container-fluid">
  <h2>Questions &amp; Answers</h2>
    <xsl:for-each select="category">
    <div class="category card">
        <div class="category-text card-header alert-primary">
            <div class="font-weight-bold"><xsl:value-of select="@name"/></div>
        </div>
        <div class="container-fluid p-3">
        <xsl:for-each select="question">
            <div class="question card">
                <div class="card-header">
                    <div class="font-weight-normal float-left"><xsl:value-of select="text()" disable-output-escaping="yes" /></div>
                    <div class="font-weight-normal float-right"><xsl:value-of select="@created" /></div>
                </div>
                <div class="card-body">
                     <div class="attachments mb-3">
                     <xsl:for-each select="attachment">
                        <div class="attachment">
                            <a href="{@attachmentId}" data-qna="attachment" class="badge badge-secondary"><xsl:value-of select="@id" /></a>
                        </div>
                    </xsl:for-each>
                    </div>
                    <xsl:for-each select="answer">
                        <div class="answer">
                            <div class="font-weight-light"><xsl:value-of select="text()" disable-output-escaping="yes" /><span class="badge badge-primary"><xsl:value-of select="@owner"/></span></div>
                        </div>
                    </xsl:for-each>
                </div>
            </div>
        </xsl:for-each>
        </div>
    </div>
    </xsl:for-each>
  </div>
</body>
</html>
</xsl:template>
</xsl:stylesheet>
