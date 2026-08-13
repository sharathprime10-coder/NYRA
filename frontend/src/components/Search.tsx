import React from 'react';
import ChatLayout from './layout/ChatLayout';
import { Search as SearchIcon } from 'lucide-react';

const Search: React.FC = () => {
  return (
    <ChatLayout>
      <div className="w-full h-full flex flex-col items-center justify-center p-8 animate-sweep">
        <div className="w-20 h-20 rounded-full bg-surface-variant flex items-center justify-center mb-6">
          <SearchIcon className="w-10 h-10 text-tertiary" />
        </div>
        <h2 className="text-3xl font-display font-bold text-on-surface mb-2">Global Search</h2>
        <p className="text-on-surface-variant max-w-md text-center">
          Deep semantic search across all your documents and chat history is under construction.
        </p>
      </div>
    </ChatLayout>
  );
};

export default Search;
