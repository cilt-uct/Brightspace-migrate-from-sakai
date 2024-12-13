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
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no"/>
<link rel="stylesheet" href="/shared/thirdpartylib/bootstrap-4.3.1/css/bootstrap.min.css"/>
<link rel="stylesheet" href="/shared/thirdpartylib/fontawesome-free-5.9.0-web/css/all.min.css"/>
<link rel="stylesheet" href="/shared/HTML-Template-Library/HTML-Templates-V4/_assets/css/styles.min.css?v=20241205001"/>
<link rel="stylesheet" href="/shared/HTML-Template-Library/HTML-Templates-V4/_assets/css/custom.min.css?v=20241205001"/>
</head>
<body>
  <div id="content" class="container-fluid">
  <h1>Questions &amp; Answers</h1>
  <xsl:for-each select="category">
    <h2><xsl:value-of select="@name"/></h2>
        <div class="container-fluid p-3">
        <xsl:for-each select="question">
		<div class="question card">
		<xsl:attribute name="id">question_<xsl:value-of select="@id"/></xsl:attribute>
                <div class="card-header">
                    <div class="font-weight-bold"><xsl:value-of select="text()" disable-output-escaping="yes" /></div>
		    <div class="attachments mb-3">
                        <xsl:for-each select="attachment">
                        <div class="attachment">
				<p><a href="{@attachmentId}" data-qna="attachment" class="badge badge-secondary"><xsl:value-of select="@id" /></a></p>
                        </div>
                        </xsl:for-each>
                    </div>
                    <div class="font-weight-light">Asked <xsl:value-of select="substring(@created,0,17)" /></div>
                </div>
                <div class="card-body">
                    <xsl:for-each select="answer">
                        <div class="answer">
				<xsl:attribute name="id">answer_<xsl:value-of select="@id"/></xsl:attribute>
				<div><xsl:value-of select="text()" disable-output-escaping="yes" /></div>
				<div class="font-weight-light">Answered <xsl:value-of select="substring(@created,0,17)" /></div>
			</div>
                    </xsl:for-each>
                </div>
            </div>
        </xsl:for-each>
        </div>
  </xsl:for-each>
  </div>
</body>
</html>
</xsl:template>
</xsl:stylesheet>
