# ── 1. CloudFront Origin Access Control (OAC) ──
resource "aws_cloudfront_origin_access_control" "oac" {
  name                              = "${var.project_name}-oac-${var.environment}"
  description                       = "OAC for NotebookLM Frontend S3 Bucket"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

# ── 2. CloudFront CDN Distribution ──
resource "aws_cloudfront_distribution" "cdn" {
  enabled             = true
  is_ipv6_enabled     = true
  default_root_object = "index.html"
  price_class         = "PriceClass_200" # Includes India (ap-south-1), Europe, North America

  # ── Origin 1: S3 Static Frontend ──
  origin {
    domain_name              = aws_s3_bucket.frontend.bucket_regional_domain_name
    origin_id                = "S3-${aws_s3_bucket.frontend.id}"
    origin_access_control_id = aws_cloudfront_origin_access_control.oac.id
  }

  # ── Origin 2: Application Load Balancer (FastAPI Backend) ──
  origin {
    domain_name = aws_lb.main.dns_name
    origin_id   = "ALB-${aws_lb.main.name}"

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "http-only" # ALB listener on port 80 (or match ACM HTTPS)
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  # ── Default Cache Behavior: Frontend React SPA ──
  default_cache_behavior {
    allowed_methods        = ["GET", "HEAD", "OPTIONS"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = "S3-${aws_s3_bucket.frontend.id}"
    viewer_protocol_policy = "redirect-to-https"
    compress               = true

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    min_ttl     = 0
    default_ttl = 86400
    max_ttl     = 31536000
  }

  # ── Ordered Cache Behavior: Route /api/* directly to Backend ALB ──
  ordered_cache_behavior {
    path_pattern           = "/api/*"
    allowed_methods        = ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]
    cached_methods         = ["GET", "HEAD", "OPTIONS"]
    target_origin_id       = "ALB-${aws_lb.main.name}"
    viewer_protocol_policy = "redirect-to-https"
    compress               = true

    # Forward all headers, cookies, query strings to FastAPI backend
    forwarded_values {
      query_string = true
      headers      = ["Authorization", "Host", "Accept", "Content-Type", "Origin", "X-Request-ID"]
      cookies {
        forward = "all"
      }
    }

    min_ttl     = 0
    default_ttl = 0
    max_ttl     = 0
  }

  # ── SPA Fallback Routing (Support client routes like /workspace/:id) ──
  custom_error_response {
    error_code            = 403
    response_code         = 200
    response_page_path    = "/index.html"
    error_caching_min_ttl = 10
  }

  custom_error_response {
    error_code            = 404
    response_code         = 200
    response_page_path    = "/index.html"
    error_caching_min_ttl = 10
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }

  tags = {
    Name = "${var.project_name}-cdn-${var.environment}"
  }
}

