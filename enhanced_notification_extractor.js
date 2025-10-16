// Enhanced notification extraction script with better text capture
(() => {
    const seenNotifications = new Set();
    let notifCount = 0;

    function extractNotification(element) {
        try {
            // Generate unique ID from element
            const elementHTML = element.innerHTML || '';
            const notifId = btoa(elementHTML.substring(0, 200));

            if (seenNotifications.has(notifId)) return;
            seenNotifications.add(notifId);
            notifCount++;

            // Extract all text content carefully
            let fullText = '';
            let notificationType = 'unknown';
            let fromHandle = 'unknown';
            let fromDisplayName = '';

            // Look for user links more carefully
            const userLinks = element.querySelectorAll('a[href^="/"][role="link"]');
            if (userLinks.length > 0) {
                // The first user link is usually who triggered the notification
                const firstUserLink = userLinks[0];
                fromHandle = firstUserLink.href.split('/').pop() || 'unknown';

                // Get display name from the link
                const displayNameSpan = firstUserLink.querySelector('span');
                if (displayNameSpan) {
                    fromDisplayName = displayNameSpan.textContent;
                }
            }

            // Extract notification type from specific patterns
            const notificationTexts = element.querySelectorAll('span');
            let actionText = '';

            notificationTexts.forEach(span => {
                const text = span.textContent || '';

                // Check for notification action keywords
                if (text.includes('liked your')) {
                    notificationType = 'like';
                    actionText = text;
                } else if (text.includes('reposted') || text.includes('retweeted')) {
                    notificationType = 'retweet';
                    actionText = text;
                } else if (text.includes('replied to')) {
                    notificationType = 'reply';
                    actionText = text;
                } else if (text.includes('followed you')) {
                    notificationType = 'follow';
                    actionText = text;
                } else if (text.includes('mentioned you')) {
                    notificationType = 'mention';
                    actionText = text;
                } else if (text.includes('quoted your')) {
                    notificationType = 'quote';
                    actionText = text;
                }

                // Capture "Replying to" text specifically
                if (text.includes('Replying to')) {
                    actionText = text;
                    notificationType = 'reply';
                }
            });

            // Get the actual reply/quote content if present
            let contentText = '';
            const tweetTextElement = element.querySelector('[data-testid="tweetText"]');
            if (tweetTextElement) {
                contentText = tweetTextElement.textContent;
            }

            // Extract mentioned users from "Replying to" section
            let mentionedUsers = [];
            const replyingToElement = element.querySelector('[dir="ltr"] > span');
            if (replyingToElement && replyingToElement.textContent.includes('Replying to')) {
                // Find all @mentions in the replying to section
                const mentionLinks = element.querySelectorAll('a[href^="/"][role="link"]');
                mentionLinks.forEach(link => {
                    const href = link.href;
                    if (href && !href.includes('/status/')) {
                        const handle = href.split('/').pop();
                        if (handle && handle !== fromHandle) {
                            mentionedUsers.push('@' + handle);
                        }
                    }
                });
            }

            // Build comprehensive notification data
            const notificationData = {
                type: notificationType,
                from_handle: fromHandle,
                from_name: fromDisplayName,
                action_text: actionText,
                content: contentText,
                mentioned_users: mentionedUsers,
                full_text: element.textContent.substring(0, 500),
                timestamp: new Date().toISOString()
            };

            console.log('__ENHANCED_NOTIFICATION__:' + JSON.stringify(notificationData));
            return notificationData;

        } catch (error) {
            console.error('Error extracting notification:', error);
            return null;
        }
    }

    // Process existing notifications
    const existingNotifs = document.querySelectorAll('article, [data-testid="cellInnerDiv"]');
    console.log(`Found ${existingNotifs.length} existing notification elements`);
    existingNotifs.forEach(extractNotification);

    // Monitor for new notifications
    const observer = new MutationObserver((mutations) => {
        mutations.forEach(mutation => {
            mutation.addedNodes.forEach(node => {
                if (node.nodeType === Node.ELEMENT_NODE && node.querySelectorAll) {
                    const notifElements = node.querySelectorAll('article, [data-testid="cellInnerDiv"]');
                    notifElements.forEach(extractNotification);
                }
            });
        });
    });

    observer.observe(document.body, {
        childList: true,
        subtree: true,
        characterData: true
    });

    console.log('Enhanced notification observer active');
    return notifCount;
})();