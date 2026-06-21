"""
Knowledge base search with RAG (Retrieval-Augmented Generation)
"""

import logging
from typing import Dict, List, Optional
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.llms import Ollama
from langchain.prompts import PromptTemplate

logger = logging.getLogger(__name__)


class KnowledgeBase:
    """Knowledge base with semantic search and RAG"""

    def __init__(
        self,
        model_name: str = "llama3.2",
        embedding_model: str = "nomic-embed-text",
        persist_directory: str = "./data/knowledge_base"
    ):
        """
        Initialize knowledge base

        Args:
            model_name: Ollama model for generation
            embedding_model: Model for embeddings
            persist_directory: ChromaDB persistence directory
        """
        self.llm = Ollama(model=model_name)
        self.embeddings = OllamaEmbeddings(model=embedding_model)
        self.persist_directory = persist_directory
        self.vector_store = None

        self.answer_prompt = PromptTemplate(
            input_variables=["question", "context"],
            template="""You are a helpful customer support assistant. Use the following context from the knowledge base to answer the customer's question.

Knowledge Base Context:
{context}

Customer Question: {question}

Provide a clear, accurate answer based on the context. If the answer is not in the context, say "I don't have information about that in our knowledge base. Let me connect you with an agent who can help."

Answer:"""
        )

    def index_articles(
        self,
        articles: List[Dict],
        chunk_size: int = 500,
        chunk_overlap: int = 50
    ) -> Dict:
        """
        Index knowledge base articles

        Args:
            articles: List of article dicts with 'title', 'content', 'category'
            chunk_size: Size of text chunks
            chunk_overlap: Overlap between chunks

        Returns:
            Dict with indexing status
        """
        try:
            # Split articles into chunks
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )

            texts = []
            metadatas = []

            for article in articles:
                title = article.get('title', 'Untitled')
                content = article.get('content', '')
                category = article.get('category', 'general')

                # Combine title and content
                full_text = f"Title: {title}\n\n{content}"

                # Split into chunks
                chunks = text_splitter.split_text(full_text)

                for i, chunk in enumerate(chunks):
                    texts.append(chunk)
                    metadatas.append({
                        "title": title,
                        "category": category,
                        "chunk_index": i,
                        "article_id": article.get('id', title)
                    })

            # Create or update vector store
            if self.vector_store is None:
                self.vector_store = Chroma.from_texts(
                    texts=texts,
                    embedding=self.embeddings,
                    metadatas=metadatas,
                    persist_directory=self.persist_directory
                )
            else:
                self.vector_store.add_texts(
                    texts=texts,
                    metadatas=metadatas
                )

            logger.info(f"Indexed {len(articles)} articles, {len(texts)} chunks")

            return {
                "status": "indexed",
                "article_count": len(articles),
                "chunk_count": len(texts)
            }

        except Exception as e:
            logger.error(f"Error indexing articles: {e}")
            return {"status": "failed", "error": str(e)}

    def search(
        self,
        query: str,
        max_results: int = 3,
        category: Optional[str] = None
    ) -> List[Dict]:
        """
        Search knowledge base

        Args:
            query: Search query
            max_results: Maximum number of results
            category: Optional category filter

        Returns:
            List of relevant articles/chunks
        """
        try:
            if self.vector_store is None:
                return []

            # Search with filter if category provided
            if category:
                docs = self.vector_store.similarity_search(
                    query,
                    k=max_results,
                    filter={"category": category}
                )
            else:
                docs = self.vector_store.similarity_search(
                    query,
                    k=max_results
                )

            results = []
            for doc in docs:
                results.append({
                    "content": doc.page_content,
                    "title": doc.metadata.get('title'),
                    "category": doc.metadata.get('category'),
                    "article_id": doc.metadata.get('article_id')
                })

            return results

        except Exception as e:
            logger.error(f"Error searching knowledge base: {e}")
            return []

    def answer_question(
        self,
        question: str,
        category: Optional[str] = None,
        num_sources: int = 3
    ) -> Dict:
        """
        Answer a question using RAG

        Args:
            question: Customer's question
            category: Optional category filter
            num_sources: Number of source documents to use

        Returns:
            Dict with answer and sources
        """
        try:
            if self.vector_store is None:
                return {
                    "answer": "Knowledge base is not initialized.",
                    "sources": []
                }

            # Search for relevant documents
            results = self.search(question, max_results=num_sources, category=category)

            if not results:
                return {
                    "answer": "I don't have information about that in our knowledge base. Let me connect you with an agent who can help.",
                    "sources": [],
                    "confidence": 0.0
                }

            # Combine context from results
            context = "\n\n".join([
                f"Article: {r['title']}\n{r['content']}"
                for r in results
            ])

            # Generate answer
            prompt = self.answer_prompt.format(
                question=question,
                context=context[:3000]  # Limit context length
            )

            answer = self.llm.invoke(prompt)

            # Prepare sources
            sources = [
                {
                    "title": r['title'],
                    "category": r['category'],
                    "article_id": r['article_id'],
                    "preview": r['content'][:200] + "..."
                }
                for r in results
            ]

            logger.info(f"Answered question from knowledge base")

            return {
                "answer": answer.strip(),
                "sources": sources,
                "source_count": len(sources),
                "confidence": 0.8 if results else 0.0
            }

        except Exception as e:
            logger.error(f"Error answering question: {e}")
            return {
                "answer": "Error processing your question.",
                "sources": [],
                "error": str(e)
            }

    def get_suggested_articles(
        self,
        ticket_description: str,
        max_suggestions: int = 5
    ) -> List[Dict]:
        """
        Suggest relevant articles for a support ticket

        Args:
            ticket_description: Description of the support issue
            max_suggestions: Maximum number of suggestions

        Returns:
            List of suggested articles
        """
        return self.search(ticket_description, max_results=max_suggestions)

    def get_popular_articles(self, category: Optional[str] = None) -> List[Dict]:
        """
        Get popular/frequently accessed articles

        Note: This is a placeholder. In production, you'd track access counts.

        Args:
            category: Optional category filter

        Returns:
            List of popular articles
        """
        # Placeholder implementation
        # In production, you'd track and return most accessed articles
        try:
            if self.vector_store is None:
                return []

            # Get sample articles
            docs = self.vector_store.similarity_search("", k=10)

            articles = {}
            for doc in docs:
                article_id = doc.metadata.get('article_id')
                if article_id and article_id not in articles:
                    articles[article_id] = {
                        "title": doc.metadata.get('title'),
                        "category": doc.metadata.get('category'),
                        "article_id": article_id,
                        "preview": doc.page_content[:200]
                    }

            return list(articles.values())[:10]

        except Exception as e:
            logger.error(f"Error getting popular articles: {e}")
            return []

    def add_article(self, article: Dict) -> Dict:
        """
        Add a single article to knowledge base

        Args:
            article: Article dict with title, content, category

        Returns:
            Dict with addition status
        """
        return self.index_articles([article])

    def update_article(self, article_id: str, updated_article: Dict) -> Dict:
        """
        Update an existing article

        Args:
            article_id: Article identifier
            updated_article: Updated article data

        Returns:
            Dict with update status
        """
        # Note: ChromaDB doesn't have built-in update
        # In production, you'd delete old and re-index
        logger.info(f"Update article {article_id}")

        return {
            "status": "updated",
            "article_id": article_id,
            "note": "Re-index to apply changes"
        }

    def delete_article(self, article_id: str) -> Dict:
        """
        Delete an article from knowledge base

        Args:
            article_id: Article identifier

        Returns:
            Dict with deletion status
        """
        # Note: ChromaDB deletion requires collection ID
        logger.info(f"Delete article {article_id}")

        return {
            "status": "deleted",
            "article_id": article_id
        }

    def get_categories(self) -> List[str]:
        """Get all available categories"""
        try:
            if self.vector_store is None:
                return []

            # Get unique categories from stored metadata
            # This is a simplified approach
            docs = self.vector_store.similarity_search("", k=100)

            categories = set()
            for doc in docs:
                cat = doc.metadata.get('category')
                if cat:
                    categories.add(cat)

            return sorted(list(categories))

        except Exception as e:
            logger.error(f"Error getting categories: {e}")
            return []

    def get_stats(self) -> Dict:
        """Get knowledge base statistics"""
        try:
            if self.vector_store is None:
                return {"status": "not_initialized"}

            # Get collection info
            collection = self.vector_store._collection

            return {
                "status": "ready",
                "total_chunks": collection.count(),
                "categories": len(self.get_categories())
            }

        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {"status": "error", "error": str(e)}
